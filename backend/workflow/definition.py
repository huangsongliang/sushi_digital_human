"""流程定义模块

包含：
- 流程节点类型定义（开始、结束、任务、条件、并行、循环）
- 流程验证器
- JSON/YAML格式解析器
"""

import json
from enum import Enum
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, model_validator

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class NodeType(str, Enum):
    """流程节点类型枚举"""

    START = "start"
    END = "end"
    TASK = "task"
    CONDITION = "condition"
    PARALLEL = "parallel"
    LOOP = "loop"


class WorkflowNode(BaseModel):
    """流程节点基类"""

    id: str = Field(..., description="节点唯一标识")
    type: NodeType = Field(..., description="节点类型")
    name: str = Field(..., description="节点名称")
    next_nodes: List[str] = Field(default_factory=list, description="后续节点ID列表")

    model_config = {"extra": "allow"}


class StartNode(WorkflowNode):
    """开始节点"""

    type: NodeType = NodeType.START


class EndNode(WorkflowNode):
    """结束节点"""

    type: NodeType = NodeType.END
    next_nodes: List[str] = []


class TaskNode(WorkflowNode):
    """任务节点"""

    type: NodeType = NodeType.TASK
    task_type: str = Field(..., description="任务类型")
    task_config: Dict[str, Any] = Field(default_factory=dict, description="任务配置")


class ConditionNode(WorkflowNode):
    """条件节点"""

    type: NodeType = NodeType.CONDITION
    condition: str = Field(..., description="条件表达式")
    true_branch: str = Field(..., description="条件为真时的下一节点ID")
    false_branch: str = Field(..., description="条件为假时的下一节点ID")

    @model_validator(mode="after")
    def validate_branches(self) -> "ConditionNode":
        """验证分支配置"""
        if self.true_branch == self.false_branch:
            raise ValueError("true_branch 和 false_branch 不能相同")
        self.next_nodes = [self.true_branch, self.false_branch]
        return self


class ParallelNode(WorkflowNode):
    """并行节点"""

    type: NodeType = NodeType.PARALLEL
    branches: List[List[str]] = Field(..., description="并行分支的节点ID列表")
    join_node: str = Field(..., description="汇合节点ID")

    @model_validator(mode="after")
    def validate_branches(self) -> "ParallelNode":
        """验证并行分支配置"""
        if len(self.branches) < 2:
            raise ValueError("并行节点至少需要两个分支")
        # 将所有分支的第一个节点添加到 next_nodes
        for branch in self.branches:
            if branch:
                self.next_nodes.append(branch[0])
        return self


class LoopNode(WorkflowNode):
    """循环节点"""

    type: NodeType = NodeType.LOOP
    loop_condition: str = Field(..., description="循环条件表达式")
    loop_body: List[str] = Field(..., description="循环体节点ID列表")
    exit_node: str = Field(..., description="循环退出后的节点ID")

    @model_validator(mode="after")
    def validate_loop(self) -> "LoopNode":
        """验证循环配置"""
        if not self.loop_body:
            raise ValueError("循环体不能为空")
        if self.loop_body[0] not in self.next_nodes:
            self.next_nodes.append(self.loop_body[0])
        return self


class WorkflowDefinition(BaseModel):
    """流程定义模型"""

    id: str = Field(..., description="流程唯一标识")
    name: str = Field(..., description="流程名称")
    description: Optional[str] = Field(default=None, description="流程描述")
    version: str = Field(..., description="流程版本")
    nodes: List[WorkflowNode] = Field(default_factory=list, description="节点列表")
    start_node_id: str = Field(..., description="开始节点ID")
    created_at: Optional[str] = Field(default=None, description="创建时间")
    updated_at: Optional[str] = Field(default=None, description="更新时间")

    def get_node_by_id(self, node_id: str) -> Optional[WorkflowNode]:
        """根据ID获取节点"""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def get_start_node(self) -> Optional[WorkflowNode]:
        """获取开始节点"""
        return self.get_node_by_id(self.start_node_id)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump(by_alias=True)


class WorkflowValidator:
    """流程验证器"""

    @staticmethod
    def validate(definition: WorkflowDefinition) -> List[str]:
        """验证流程定义

        Args:
            definition: 流程定义

        Returns:
            错误信息列表，如果验证通过则返回空列表
        """
        errors = []

        # 检查开始节点
        start_node = definition.get_start_node()
        if not start_node:
            errors.append(f"开始节点 {definition.start_node_id} 不存在")
        elif start_node.type != NodeType.START:
            errors.append(f"节点 {definition.start_node_id} 不是开始节点")

        # 检查节点ID唯一性
        node_ids = [node.id for node in definition.nodes]
        if len(node_ids) != len(set(node_ids)):
            errors.append("存在重复的节点ID")

        # 检查每个节点的后续节点是否存在
        for node in definition.nodes:
            for next_node_id in node.next_nodes:
                if not definition.get_node_by_id(next_node_id):
                    errors.append(f"节点 {node.id} 的后续节点 {next_node_id} 不存在")

        # 检查条件节点的分支
        for node in definition.nodes:
            if isinstance(node, ConditionNode):
                if not definition.get_node_by_id(node.true_branch):
                    errors.append(f"条件节点 {node.id} 的 true_branch {node.true_branch} 不存在")
                if not definition.get_node_by_id(node.false_branch):
                    errors.append(f"条件节点 {node.id} 的 false_branch {node.false_branch} 不存在")

        # 检查并行节点的分支和汇合节点
        for node in definition.nodes:
            if isinstance(node, ParallelNode):
                for branch in node.branches:
                    for node_id in branch:
                        if not definition.get_node_by_id(node_id):
                            errors.append(f"并行节点 {node.id} 的分支节点 {node_id} 不存在")
                if not definition.get_node_by_id(node.join_node):
                    errors.append(f"并行节点 {node.id} 的汇合节点 {node.join_node} 不存在")

        # 检查循环节点
        for node in definition.nodes:
            if isinstance(node, LoopNode):
                for node_id in node.loop_body:
                    if not definition.get_node_by_id(node_id):
                        errors.append(f"循环节点 {node.id} 的循环体节点 {node_id} 不存在")
                if not definition.get_node_by_id(node.exit_node):
                    errors.append(f"循环节点 {node.id} 的退出节点 {node.exit_node} 不存在")

        # 检查是否有结束节点
        has_end_node = any(node.type == NodeType.END for node in definition.nodes)
        if not has_end_node:
            errors.append("流程必须包含至少一个结束节点")

        return errors

    @staticmethod
    def is_valid(definition: WorkflowDefinition) -> bool:
        """检查流程定义是否有效"""
        return len(WorkflowValidator.validate(definition)) == 0


class WorkflowParser:
    """流程解析器 - 支持 JSON/YAML 格式"""

    @staticmethod
    def from_json(json_str: str) -> WorkflowDefinition:
        """从JSON字符串解析流程定义"""
        try:
            data = json.loads(json_str)
            return WorkflowParser._parse(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON解析错误: {str(e)}")

    @staticmethod
    def from_yaml(yaml_str: str) -> WorkflowDefinition:
        """从YAML字符串解析流程定义"""
        try:
            data = yaml.safe_load(yaml_str)
            return WorkflowParser._parse(data)
        except yaml.YAMLError as e:
            raise ValueError(f"YAML解析错误: {str(e)}")

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> WorkflowDefinition:
        """从字典解析流程定义"""
        return WorkflowParser._parse(data)

    @staticmethod
    def _parse(data: Dict[str, Any]) -> WorkflowDefinition:
        """内部解析方法"""
        # 解析节点
        nodes = []
        for node_data in data.get("nodes", []):
            node_type = NodeType(node_data.get("type"))
            node_class = WorkflowParser._get_node_class(node_type)
            nodes.append(node_class(**node_data))

        data["nodes"] = nodes
        return WorkflowDefinition(**data)

    @staticmethod
    def _get_node_class(node_type: NodeType):
        """根据节点类型获取对应的类"""
        mapping = {
            NodeType.START: StartNode,
            NodeType.END: EndNode,
            NodeType.TASK: TaskNode,
            NodeType.CONDITION: ConditionNode,
            NodeType.PARALLEL: ParallelNode,
            NodeType.LOOP: LoopNode,
        }
        return mapping.get(node_type, WorkflowNode)

    @staticmethod
    def to_json(definition: WorkflowDefinition) -> str:
        """转换为JSON字符串"""
        return json.dumps(definition.to_dict(), ensure_ascii=False, indent=2)

    @staticmethod
    def to_yaml(definition: WorkflowDefinition) -> str:
        """转换为YAML字符串"""
        return yaml.dump(definition.to_dict(), default_flow_style=False, allow_unicode=True)
