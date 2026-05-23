"""版本管理模块 - 支持版本注册、对比和灰度发布"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class VersionStatus(Enum):
    """版本状态"""

    DRAFT = "draft"
    STAGING = "staging"
    CANARY = "canary"
    PRODUCTION = "production"
    ROLLBACK = "rollback"
    DEPRECATED = "deprecated"


class VersionType(Enum):
    """版本类型"""

    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    HOTFIX = "hotfix"


@dataclass
class VersionMetadata:
    """版本元数据"""

    created_at: datetime
    created_by: str
    updated_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    changelog: str = ""
    dependencies: Dict[str, str] = field(default_factory=dict)
    environment: str = "production"
    rollout_percentage: float = 0.0


@dataclass
class DeploymentVersion:
    """部署版本"""

    version_id: str
    version_name: str
    version_code: str
    version_type: VersionType
    status: VersionStatus
    metadata: VersionMetadata
    config: Dict[str, Any] = field(default_factory=dict)
    rollout_config: Dict[str, Any] = field(default_factory=dict)
    health_check: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.version_type, str):
            self.version_type = VersionType(self.version_type)
        if isinstance(self.status, str):
            self.status = VersionStatus(self.status)
        if not isinstance(self.metadata, VersionMetadata):
            self.metadata = (
                VersionMetadata(**self.metadata)
                if isinstance(self.metadata, dict)
                else VersionMetadata(created_at=datetime.now(), created_by="system")
            )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "version_id": self.version_id,
            "version_name": self.version_name,
            "version_code": self.version_code,
            "version_type": self.version_type.value,
            "status": self.status.value,
            "metadata": {
                "created_at": self.metadata.created_at.isoformat(),
                "created_by": self.metadata.created_by,
                "updated_at": self.metadata.updated_at.isoformat() if self.metadata.updated_at else None,
                "tags": self.metadata.tags,
                "changelog": self.metadata.changelog,
                "dependencies": self.metadata.dependencies,
                "environment": self.metadata.environment,
                "rollout_percentage": self.metadata.rollout_percentage,
            },
            "config": self.config,
            "rollout_config": self.rollout_config,
            "health_check": self.health_check,
            "metrics": self.metrics,
        }

    @staticmethod
    def compare_versions(version1: str, version2: str) -> int:
        """比较两个语义化版本号

        返回:
            -1: version1 < version2
             0: version1 == version2
             1: version1 > version2
        """

        def parse_version(v: str) -> tuple:
            parts = v.lstrip("vV").split(".")
            return tuple(int(p) for p in parts[:3]) + (0,) * (3 - len(parts[:3]))

        v1_parts = parse_version(version1)
        v2_parts = parse_version(version2)

        if v1_parts < v2_parts:
            return -1
        elif v1_parts > v2_parts:
            return 1
        else:
            return 0


class VersionManager:
    """版本管理器"""

    def __init__(self):
        self._versions: Dict[str, DeploymentVersion] = {}
        self._version_history: Dict[str, List[str]] = {}

    def register_version(
        self,
        version_name: str,
        version_code: str,
        version_type: VersionType,
        created_by: str,
        config: Optional[Dict[str, Any]] = None,
        changelog: str = "",
        tags: Optional[List[str]] = None,
        dependencies: Optional[Dict[str, str]] = None,
    ) -> DeploymentVersion:
        """注册新版本"""
        version_id = self._generate_version_id(version_name, version_code)

        if version_id in self._versions:
            raise ValueError(f"版本 {version_code} 已存在")

        metadata = VersionMetadata(
            created_at=datetime.now(),
            created_by=created_by,
            tags=tags or [],
            changelog=changelog,
            dependencies=dependencies or {},
        )

        version = DeploymentVersion(
            version_id=version_id,
            version_name=version_name,
            version_code=version_code,
            version_type=version_type,
            status=VersionStatus.DRAFT,
            metadata=metadata,
            config=config or {},
        )

        self._versions[version_id] = version
        self._version_history[version_id] = [version_id]

        logger.info(f"注册新版本: {version_name} ({version_code})")
        return version

    def get_version(self, version_id: str) -> Optional[DeploymentVersion]:
        """获取版本信息"""
        return self._versions.get(version_id)

    def get_version_by_code(self, version_code: str) -> Optional[DeploymentVersion]:
        """根据版本号获取版本"""
        for version in self._versions.values():
            if version.version_code == version_code:
                return version
        return None

    def list_versions(
        self,
        status: Optional[VersionStatus] = None,
        tags: Optional[List[str]] = None,
    ) -> List[DeploymentVersion]:
        """列出版本"""
        versions = list(self._versions.values())

        if status:
            versions = [v for v in versions if v.status == status]

        if tags:
            versions = [v for v in versions if any(tag in v.metadata.tags for tag in tags)]

        versions.sort(key=lambda v: v.metadata.created_at, reverse=True)
        return versions

    def update_version_status(self, version_id: str, status: VersionStatus) -> bool:
        """更新版本状态"""
        if version_id not in self._versions:
            return False

        version = self._versions[version_id]
        old_status = version.status
        version.status = status
        version.metadata.updated_at = datetime.now()

        if version_id in self._version_history:
            self._version_history[version_id].append(status.value)

        logger.info(f"更新版本状态: {version.version_code} ({old_status.value} -> {status.value})")
        return True

    def update_rollout_percentage(self, version_id: str, percentage: float) -> bool:
        """更新灰度发布百分比"""
        if version_id not in self._versions:
            return False

        if not 0 <= percentage <= 100:
            raise ValueError("百分比必须在 0-100 之间")

        version = self._versions[version_id]
        version.metadata.rollout_percentage = percentage
        version.metadata.updated_at = datetime.now()

        logger.info(f"更新灰度百分比: {version.version_code} -> {percentage}%")
        return True

    def add_tag(self, version_id: str, tag: str) -> bool:
        """为版本添加标签"""
        if version_id not in self._versions:
            return False

        version = self._versions[version_id]
        if tag not in version.metadata.tags:
            version.metadata.tags.append(tag)
            version.metadata.updated_at = datetime.now()

        return True

    def update_metrics(self, version_id: str, metrics: Dict[str, Any]) -> bool:
        """更新版本指标"""
        if version_id not in self._versions:
            return False

        version = self._versions[version_id]
        version.metrics.update(metrics)
        return True

    def compare_with_previous(self, version_id: str) -> Dict[str, Any]:
        """与前一个版本对比"""
        if version_id not in self._versions:
            return {}

        version = self._versions[version_id]
        versions = self._version_history.get(version_id, [])

        if len(versions) < 2:
            return {"message": "没有可对比的历史版本"}

        previous_code = versions[-2] if len(versions) > 1 else None
        if not previous_code:
            return {"message": "没有可对比的历史版本"}

        previous_version = self.get_version(previous_code)
        if not previous_version:
            return {"message": "历史版本不存在"}

        return {
            "current_version": version.to_dict(),
            "previous_version": previous_version.to_dict(),
            "comparison": {
                "config_changes": self._diff_configs(version.config, previous_version.config),
                "metrics_comparison": self._compare_metrics(version.metrics, previous_version.metrics),
            },
        }

    def _diff_configs(self, config1: Dict[str, Any], config2: Dict[str, Any]) -> Dict[str, Any]:
        """对比配置差异"""
        added = {k: config1[k] for k in config1 if k not in config2}
        removed = {k: config2[k] for k in config2 if k not in config1}
        modified = {
            k: {"old": config2[k], "new": config1[k]} for k in config1 if k in config2 and config1[k] != config2[k]
        }

        return {
            "added": added,
            "removed": removed,
            "modified": modified,
        }

    def _compare_metrics(self, metrics1: Dict[str, Any], metrics2: Dict[str, Any]) -> Dict[str, Any]:
        """对比指标"""
        comparison = {}

        numeric_keys = {"requests", "errors", "latency_avg", "latency_p99", "success_rate"}

        for key in numeric_keys:
            if key in metrics1 and key in metrics2:
                val1 = float(metrics1[key])
                val2 = float(metrics2[key])
                if val2 != 0:
                    change_pct = ((val1 - val2) / val2) * 100
                else:
                    change_pct = 0 if val1 == 0 else 100

                comparison[key] = {
                    "current": val1,
                    "previous": val2,
                    "change_percent": round(change_pct, 2),
                }

        return comparison

    def _generate_version_id(self, name: str, code: str) -> str:
        """生成版本 ID"""
        hash_input = f"{name}{code}{datetime.now().isoformat()}"
        return hashlib.md5(hash_input.encode(), usedforsecurity=False).hexdigest()[:16]

    def get_latest_production_version(self) -> Optional[DeploymentVersion]:
        """获取最新的生产版本"""
        production_versions = [v for v in self._versions.values() if v.status == VersionStatus.PRODUCTION]
        if not production_versions:
            return None

        return max(production_versions, key=lambda v: v.metadata.created_at)

    def rollback_version(self, version_id: str) -> bool:
        """回滚版本"""
        if version_id not in self._versions:
            return False

        _version = self._versions[version_id]  # noqa: F841
        return self.update_version_status(version_id, VersionStatus.ROLLBACK)


_version_manager = VersionManager()


def get_version_manager() -> VersionManager:
    """获取版本管理器实例"""
    return _version_manager
