---
description: Python 后端代码规范（PEP8 + FastAPI 最佳实践）
alwaysApply: true
---

# Python / FastAPI 代码规范

## 导入规范

```python
# 标准库
import os
from pathlib import Path
from typing import List, Dict, Optional, AsyncGenerator

# 第三方库
from fastapi import APIRouter, Depends, HTTPException, status
from langchain.chains import LLMChain
from pydantic import BaseModel, Field

# 项目内部模块
from backend.core.config import settings
from backend.database.session import get_db
from backend.utils.logger import get_logger
```

**禁止**在函数/类内部导入模块（type annotation 用的 `TYPE_CHECKING` 除外）。

## 注释与文档字符串

```python
"""模块级文档字符串：说明本模块的用途和主要功能"""

class MyClass:
    """类文档字符串：说明类的职责、使用方法、注意事项"""

    def my_method(self, param: str) -> bool:
        """方法文档字符串：说明功能、参数、返回值

        Args:
            param: 参数说明

        Returns:
            返回值说明

        Raises:
            ValueError: 参数错误时
        """
        # 单行注释：# 后必须有一个空格
        result = process(param)
        return result
```

## 空行规范

- 类定义前后：**两个空行**
- 顶层函数定义前后：**两个空行**
- 类内方法定义前后：**一个空行**
- 逻辑段落之间：**一个空行**

## 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 变量/函数/方法 | `snake_case` | `get_user_by_id` |
| 类名 | `PascalCase` | `RAGChain` |
| 常量 | `UPPER_SNAKE_CASE` | `MAX_RETRIES` |
| 私有属性/方法 | `_leading_underscore` | `_build_prompt` |
| 模块文件名 | `snake_case.py` | `rag_chain.py` |

## 类型注解（强制）

```python
from typing import List, Dict, Optional, AsyncGenerator

def get_user(user_id: int) -> Optional[User]:
    """所有函数参数和返回值必须有类型注解"""
    ...

def process_documents(
    files: List[UploadFile],
    chunk_size: int = 500,
    overlap: Optional[int] = None,
) -> Dict[str, Any]:
    """参数和返回值都必须有类型注解"""
    ...

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """异步生成器类型注解"""
    ...
```

## FastAPI 路由规范

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/documents", tags=["documents"])

class DocumentUploadRequest(BaseModel):
    """请求体用 Pydantic BaseModel 定义"""
    description: Optional[str] = None
    category: str = Field(..., description="文档分类")

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    req: DocumentUploadRequest = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentUploadResponse:
    """路由函数：参数用 Depends 注入，返回类型注解用 response_model"""
    ...
```

## 异常处理规范

```python
# 使用 FastAPI 的 HTTPException
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Document not found",
)

# 业务异常自定义
class BusinessException(Exception):
    def __init__(self, message: str, code: int = 400):
        self.message = message
        self.code = code
        super().__init__(message)
```

## 日志规范

```python
from backend.utils.logger import get_logger

logger = get_logger(__name__)

logger.debug("调试信息：%s", variable)
logger.info("操作成功：user_id=%s", user_id)
logger.warning("警告信息：%s", warning_detail)
logger.error("错误信息：%s", error, exc_info=True)
```

## 数据库操作规范

```python
# 使用异步 session，通过 Depends(get_db) 注入
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

# 禁止在循环内频繁 commit，批量操作后统一 commit
```

## LangChain 链规范

```python
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

# Prompt 模板统一放在 chain/prompts/ 目录
PROMPT_TEMPLATE = PromptTemplate(
    input_variables=["context", "question"],
    template="上下文：\n{context}\n\n问题：{question}\n答案：",
)

# Chain 用 LCEL 写法（LangChain 0.3+）
chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt
    | llm
    | output_parser
)
```
