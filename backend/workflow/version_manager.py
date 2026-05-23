"""流程版本管理模块

包含：
- 版本存储
- 版本对比
- 回滚功能
"""

import json
import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from backend.utils.logger import get_logger
from backend.workflow.definition import WorkflowDefinition, WorkflowParser

logger = get_logger(__name__)


class VersionInfo(BaseModel):
    """版本信息模型"""

    version: str = Field(..., description="版本号")
    workflow_id: str = Field(..., description="流程ID")
    created_at: str = Field(..., description="创建时间")
    description: Optional[str] = Field(default=None, description="版本描述")
    is_active: bool = Field(default=False, description="是否为当前活跃版本")


class VersionDiff(BaseModel):
    """版本对比结果"""

    workflow_id: str = Field(..., description="流程ID")
    from_version: str = Field(..., description="源版本")
    to_version: str = Field(..., description="目标版本")
    added_nodes: List[str] = Field(default_factory=list, description="新增节点ID列表")
    removed_nodes: List[str] = Field(default_factory=list, description="删除节点ID列表")
    modified_nodes: List[str] = Field(default_factory=list, description="修改节点ID列表")
    changed_config: List[str] = Field(default_factory=list, description="变更的配置项")


class WorkflowVersionManager:
    """流程版本管理器"""

    def __init__(self):
        self._versions: Dict[str, List[Dict[str, Any]]] = {}
        self._active_versions: Dict[str, str] = {}

    def save_version(self, definition: WorkflowDefinition, description: Optional[str] = None) -> VersionInfo:
        """保存流程版本

        Args:
            definition: 流程定义
            description: 版本描述

        Returns:
            版本信息
        """
        version_info = {
            "version": definition.version,
            "workflow_id": definition.id,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "description": description,
            "definition": WorkflowParser.to_json(definition),
            "is_active": False,
        }

        if definition.id not in self._versions:
            self._versions[definition.id] = []

        self._versions[definition.id].append(version_info)

        # 设置为活跃版本（首次保存时）
        if definition.id not in self._active_versions:
            self._active_versions[definition.id] = definition.version
            version_info["is_active"] = True

        logger.info(f"保存流程版本: {definition.id} v{definition.version}")

        return VersionInfo(**{k: v for k, v in version_info.items() if k != "definition"})

    def get_version(self, workflow_id: str, version: str) -> Optional[WorkflowDefinition]:
        """获取指定版本的流程定义

        Args:
            workflow_id: 流程ID
            version: 版本号

        Returns:
            流程定义，如果不存在则返回None
        """
        versions = self._versions.get(workflow_id, [])
        for v in versions:
            if v["version"] == version:
                return WorkflowParser.from_json(v["definition"])
        return None

    def get_active_version(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """获取当前活跃版本的流程定义

        Args:
            workflow_id: 流程ID

        Returns:
            流程定义，如果不存在则返回None
        """
        active_version = self._active_versions.get(workflow_id)
        if not active_version:
            return None
        return self.get_version(workflow_id, active_version)

    def list_versions(self, workflow_id: str) -> List[VersionInfo]:
        """获取流程的所有版本列表

        Args:
            workflow_id: 流程ID

        Returns:
            版本信息列表
        """
        versions = self._versions.get(workflow_id, [])
        return [VersionInfo(**{k: v for k, v in version.items() if k != "definition"}) for version in versions]

    def rollback(self, workflow_id: str, target_version: str) -> bool:
        """回滚到指定版本

        Args:
            workflow_id: 流程ID
            target_version: 目标版本号

        Returns:
            回滚是否成功
        """
        if workflow_id not in self._versions:
            logger.error(f"流程不存在: {workflow_id}")
            return False

        versions = self._versions[workflow_id]
        version_exists = any(v["version"] == target_version for v in versions)

        if not version_exists:
            logger.error(f"版本不存在: {target_version}")
            return False

        self._active_versions[workflow_id] = target_version

        # 更新版本的活跃状态
        for v in versions:
            v["is_active"] = (v["version"] == target_version)

        logger.info(f"流程 {workflow_id} 已回滚到版本 {target_version}")
        return True

    def compare_versions(self, workflow_id: str, from_version: str, to_version: str) -> Optional[VersionDiff]:
        """对比两个版本的差异

        Args:
            workflow_id: 流程ID
            from_version: 源版本号
            to_version: 目标版本号

        Returns:
            版本差异信息，如果版本不存在则返回None
        """
        from_def = self.get_version(workflow_id, from_version)
        to_def = self.get_version(workflow_id, to_version)

        if not from_def or not to_def:
            return None

        from_nodes = {node.id: node for node in from_def.nodes}
        to_nodes = {node.id: node for node in to_def.nodes}

        added_nodes = [node_id for node_id in to_nodes if node_id not in from_nodes]
        removed_nodes = [node_id for node_id in from_nodes if node_id not in to_nodes]
        modified_nodes = []

        for node_id in set(from_nodes.keys()) & set(to_nodes.keys()):
            from_node = from_nodes[node_id]
            to_node = to_nodes[node_id]

            if from_node.model_dump() != to_node.model_dump():
                modified_nodes.append(node_id)

        changed_config = []
        if from_def.name != to_def.name:
            changed_config.append("name")
        if from_def.description != to_def.description:
            changed_config.append("description")
        if from_def.start_node_id != to_def.start_node_id:
            changed_config.append("start_node_id")

        return VersionDiff(
            workflow_id=workflow_id,
            from_version=from_version,
            to_version=to_version,
            added_nodes=added_nodes,
            removed_nodes=removed_nodes,
            modified_nodes=modified_nodes,
            changed_config=changed_config,
        )

    def delete_version(self, workflow_id: str, version: str) -> bool:
        """删除指定版本

        Args:
            workflow_id: 流程ID
            version: 版本号

        Returns:
            删除是否成功
        """
        if workflow_id not in self._versions:
            return False

        versions = self._versions[workflow_id]
        original_count = len(versions)

        self._versions[workflow_id] = [v for v in versions if v["version"] != version]

        # 如果删除的是活跃版本，将活跃版本设置为最新的版本
        if self._active_versions.get(workflow_id) == version:
            remaining_versions = self._versions[workflow_id]
            if remaining_versions:
                self._active_versions[workflow_id] = remaining_versions[-1]["version"]
                remaining_versions[-1]["is_active"] = True
            else:
                del self._active_versions[workflow_id]

        logger.info(f"删除流程版本: {workflow_id} v{version}")
        return len(versions) > original_count

    def get_version_history(self, workflow_id: str) -> List[Dict[str, Any]]:
        """获取版本历史记录（包含完整定义）

        Args:
            workflow_id: 流程ID

        Returns:
            版本历史列表
        """
        return self._versions.get(workflow_id, [])


# 全局版本管理器实例
_version_manager = WorkflowVersionManager()


def get_version_manager() -> WorkflowVersionManager:
    """获取全局版本管理器实例"""
    return _version_manager
