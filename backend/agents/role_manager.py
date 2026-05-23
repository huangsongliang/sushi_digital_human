"""角色管理模块

负责Agent角色的定义、CRUD操作和角色分配逻辑。
"""

from enum import Enum
from typing import Dict, List, Optional, Set, Union

from pydantic import BaseModel, Field
from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class AgentCapability(str, Enum):
    """Agent能力枚举"""

    DOCUMENT_RETRIEVAL = "document_retrieval"
    DOCUMENT_SUMMARIZATION = "document_summarization"
    KNOWLEDGE_GRAPH_QUERY = "knowledge_graph_query"
    LLM_CHAT = "llm_chat"
    MULTIMODAL_ANALYSIS = "multimodal_analysis"
    CODE_GENERATION = "code_generation"
    DATA_ANALYSIS = "data_analysis"
    TASK_PLANNING = "task_planning"


class AgentRole(BaseModel):
    """Agent角色数据模型"""

    id: Optional[int] = Field(default=None, description="角色ID")
    name: str = Field(..., description="角色名称")
    description: Optional[str] = Field(default=None, description="角色描述")
    capabilities: List[AgentCapability] = Field(default_factory=list, description="角色能力列表")
    is_active: bool = Field(default=True, description="是否启用")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "name": "文档检索专家",
                "description": "负责文档检索和信息提取",
                "capabilities": ["document_retrieval", "knowledge_graph_query"],
                "is_active": True,
            }
        }
    }


class RoleManager:
    """角色管理类"""

    def __init__(self):
        self._roles: Dict[str, AgentRole] = {}

    async def create_role(
        self,
        name: str,
        description: Optional[str] = None,
        capabilities: Optional[List[AgentCapability]] = None,
        db: Optional[AsyncSession] = None,
    ) -> AgentRole:
        """创建新角色

        Args:
            name: 角色名称
            description: 角色描述
            capabilities: 角色能力列表
            db: 数据库会话（可选）

        Returns:
            创建的角色对象

        Raises:
            ValueError: 角色名称已存在
        """
        if name in self._roles:
            raise ValueError(f"角色 '{name}' 已存在")

        role = AgentRole(
            name=name,
            description=description,
            capabilities=capabilities or [],
            is_active=True,
        )

        if db:
            result = await db.execute(
                insert(RoleTable).values(
                    name=name,
                    description=description,
                    capabilities=[c.value for c in capabilities or []],
                    is_active=True,
                )
            )
            await db.commit()
            role.id = result.inserted_primary_key[0]

        self._roles[name] = role
        logger.info(f"创建角色: {name}")
        return role

    async def get_role(self, name_or_id: Union[str, int], db: Optional[AsyncSession] = None) -> Optional[AgentRole]:
        """获取角色

        Args:
            name_or_id: 角色名称或ID
            db: 数据库会话（可选）

        Returns:
            角色对象，如果不存在返回None
        """
        # 先从内存缓存查找
        if isinstance(name_or_id, str):
            if name_or_id in self._roles:
                return self._roles[name_or_id]
        else:
            for role in self._roles.values():
                if role.id == name_or_id:
                    return role

        # 从数据库查找
        if db:
            if isinstance(name_or_id, str):
                result = await db.execute(select(RoleTable).where(RoleTable.name == name_or_id))
            else:
                result = await db.execute(select(RoleTable).where(RoleTable.id == name_or_id))

            record = result.scalar_one_or_none()
            if record:
                role = AgentRole(
                    id=record.id,
                    name=record.name,
                    description=record.description,
                    capabilities=[AgentCapability(c) for c in record.capabilities],
                    is_active=record.is_active,
                )
                self._roles[record.name] = role
                return role

        return None

    async def list_roles(self, db: Optional[AsyncSession] = None) -> List[AgentRole]:
        """获取所有角色列表

        Args:
            db: 数据库会话（可选）

        Returns:
            角色列表
        """
        if db:
            result = await db.execute(select(RoleTable).where(RoleTable.is_active.is_(True)))
            records = result.scalars().all()

            roles = []
            for record in records:
                role = AgentRole(
                    id=record.id,
                    name=record.name,
                    description=record.description,
                    capabilities=[AgentCapability(c) for c in record.capabilities],
                    is_active=record.is_active,
                )
                self._roles[record.name] = role
                roles.append(role)
            return roles

        return list(self._roles.values())

    async def update_role(
        self,
        name_or_id: Union[str, int],
        new_name: Optional[str] = None,
        description: Optional[str] = None,
        capabilities: Optional[List[AgentCapability]] = None,
        is_active: Optional[bool] = None,
        db: Optional[AsyncSession] = None,
    ) -> AgentRole:
        """更新角色信息

        Args:
            name_or_id: 角色名称或ID
            new_name: 新名称（可选）
            description: 新描述（可选）
            capabilities: 新能力列表（可选）
            is_active: 是否启用（可选）
            db: 数据库会话（可选）

        Returns:
            更新后的角色对象

        Raises:
            ValueError: 角色不存在
        """
        role = await self.get_role(name_or_id, db)
        if not role:
            raise ValueError(f"角色 '{name_or_id}' 不存在")

        if new_name:
            role.name = new_name
        if description is not None:
            role.description = description
        if capabilities is not None:
            role.capabilities = capabilities
        if is_active is not None:
            role.is_active = is_active

        if db:
            update_data = {}
            if new_name:
                update_data["name"] = new_name
            if description is not None:
                update_data["description"] = description
            if capabilities is not None:
                update_data["capabilities"] = [c.value for c in capabilities]
            if is_active is not None:
                update_data["is_active"] = is_active

            if update_data:
                await db.execute(update(RoleTable).where(RoleTable.id == role.id).values(**update_data))
                await db.commit()

        if new_name and name_or_id != new_name:
            old_key = name_or_id if isinstance(name_or_id, str) else role.name
            del self._roles[old_key]
            self._roles[new_name] = role

        logger.info(f"更新角色: {role.name}")
        return role

    async def delete_role(self, name_or_id: Union[str, int], db: Optional[AsyncSession] = None) -> bool:
        """删除角色

        Args:
            name_or_id: 角色名称或ID
            db: 数据库会话（可选）

        Returns:
            删除是否成功

        Raises:
            ValueError: 角色不存在
        """
        role = await self.get_role(name_or_id, db)
        if not role:
            raise ValueError(f"角色 '{name_or_id}' 不存在")

        if db and role.id:
            await db.execute(delete(RoleTable).where(RoleTable.id == role.id))
            await db.commit()

        key = name_or_id if isinstance(name_or_id, str) else role.name
        if key in self._roles:
            del self._roles[key]

        logger.info(f"删除角色: {role.name}")
        return True

    def match_roles_by_capability(
        self,
        required_capability: AgentCapability,
        roles: Optional[List[AgentRole]] = None,
    ) -> List[AgentRole]:
        """根据能力匹配角色

        Args:
            required_capability: 需要的能力
            roles: 角色列表（可选，默认为所有角色）

        Returns:
            匹配的角色列表
        """
        target_roles = roles or list(self._roles.values())
        return [role for role in target_roles if role.is_active and required_capability in role.capabilities]

    def match_roles_by_capabilities(
        self,
        required_capabilities: Set[AgentCapability],
        roles: Optional[List[AgentRole]] = None,
    ) -> List[AgentRole]:
        """根据多个能力匹配角色

        Args:
            required_capabilities: 需要的能力集合
            roles: 角色列表（可选，默认为所有角色）

        Returns:
            匹配的角色列表（至少具备一个所需能力）
        """
        target_roles = roles or list(self._roles.values())
        return [
            role
            for role in target_roles
            if role.is_active and any(cap in role.capabilities for cap in required_capabilities)
        ]


class RoleTable:
    """角色数据库表映射（用于SQLAlchemy）"""

    __tablename__ = "agent_roles"

    id = None
    name = None
    description = None
    capabilities = None
    is_active = None
    created_at = None
    updated_at = None


# 全局角色管理器实例
role_manager = RoleManager()
