"""数据库模型定义"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Boolean,
    Float,
)
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(AsyncAttrs, DeclarativeBase):
    """基础模型类"""

    pass


class User(Base):
    """用户模型"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    conversations = relationship("Conversation", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"


class Conversation(Base):
    """对话模型"""

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(String(64), unique=True, nullable=False)
    title = Column(String(200))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")

    def __repr__(self):
        return f"<Conversation(id={self.id}, session_id={self.session_id})>"


class Message(Base):
    """消息模型"""

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    source_documents = Column(Text)  # JSON 格式存储引用文档
    token_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)

    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self):
        return f"<Message(id={self.id}, role={self.role})>"


class Document(Base):
    """文档模型 - 表示文档的单个分块"""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    source = Column(String(255), nullable=False)
    metadata_json = Column(Text)
    chunk_index = Column(Integer, default=0)
    total_chunks = Column(Integer, default=1)
    document_id = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<Document(id={self.id}, source={self.source}, chunk={self.chunk_index})>"


class DocumentLibrary(Base):
    """文档库模型 - 管理文档集合"""

    __tablename__ = "document_library"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    document_id = Column(String(64), unique=True, nullable=False)
    file_path = Column(String(500))
    file_hash = Column(String(64))
    file_size = Column(Integer, default=0)
    mime_type = Column(String(100))
    chunk_count = Column(Integer, default=0)
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<DocumentLibrary(id={self.id}, name={self.name}, ver={self.version})>"


class DocumentVersion(Base):
    """文档版本历史模型"""

    __tablename__ = "document_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(64), nullable=False)
    version = Column(Integer, default=1)
    file_path = Column(String(500))
    file_hash = Column(String(64))
    file_size = Column(Integer, default=0)
    change_log = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<DocumentVersion(doc_id={self.document_id}, ver={self.version})>"


class SystemPrompt(Base):
    """系统提示词模型"""

    __tablename__ = "system_prompts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    content = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<SystemPrompt(id={self.id}, name={self.name})>"


class ApiKey(Base):
    """API Key 模型"""

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    key = Column(String(64), unique=True, nullable=False)
    name = Column(String(100))
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User")

    def __repr__(self):
        return f"<ApiKey(id={self.id}, name={self.name})>"


class Role(Base):
    """角色模型"""

    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<Role(id={self.id}, name={self.name})>"


class Permission(Base):
    """权限模型"""

    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255))
    resource = Column(String(100))
    action = Column(String(50))
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<Permission(id={self.id}, name={self.name})>"


class UserRole(Base):
    """用户-角色关联表"""

    __tablename__ = "user_roles"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User", backref="user_roles")
    role = relationship("Role", backref="user_roles")

    def __repr__(self):
        return f"<UserRole(user_id={self.user_id}, role_id={self.role_id})>"


class RolePermission(Base):
    """角色-权限关联表"""

    __tablename__ = "role_permissions"

    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)
    permission_id = Column(Integer, ForeignKey("permissions.id"), primary_key=True)
    created_at = Column(DateTime, default=datetime.now)

    role = relationship("Role", backref="role_permissions")
    permission = relationship("Permission", backref="role_permissions")

    def __repr__(self):
        return f"<RolePermission(role_id={self.role_id}, permission_id={self.permission_id})>"


class UsageLog(Base):
    """使用日志模型"""

    __tablename__ = "usage_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(String(64))
    endpoint = Column(String(100))
    method = Column(String(10))
    status_code = Column(Integer)
    duration = Column(Float)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User")

    def __repr__(self):
        return f"<UsageLog(id={self.id}, endpoint={self.endpoint})>"
