---
description: API 接口规范、错误处理、鉴权约定
---

# API 接口与错误处理规范

## 后端 API 规范（FastAPI）

### 统一响应格式

```python
# backend/schemas/response.py
from pydantic import BaseModel, Field
from typing import Generic, TypeVar, Optional, Any

T = TypeVar('T')

class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应格式"""
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="消息")
    data: Optional[T] = Field(default=None, description="数据")

    model_config = {"arbitrary_types_allowed": True}


def success_response(data: Any = None, message: str = "success") -> ApiResponse:
    """成功响应"""
    return ApiResponse(code=200, message=message, data=data)


def error_response(code: int, message: str) -> ApiResponse:
    """错误响应"""
    return ApiResponse(code=code, message=message, data=None)
```

### 路由命名规范

```
GET    /api/documents/              # 获取列表（复数名词，结尾无斜杠）
GET    /api/documents/{id}          # 获取单条
POST   /api/documents/upload         # 上传（动作用动词）
PUT    /api/documents/{id}           # 更新
DELETE /api/documents/{id}          # 删除
GET    /api/documents/{id}/versions # 子资源用斜杠
```

### 鉴权规范

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorization:redentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """获取当前登录用户（JWT 鉴权）"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await get_user_by_id(user_id, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# 使用：路由函数加 Depends(get_current_user)
@router.get("/api/documents/list")
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[List[DocumentOut]]:
    ...
```

### 权限检查规范

```python
from backend.core.permission_manager import require_permission

@router.delete("/api/documents/{doc_id}")
@require_permission("document:delete")  # 装饰器方式
async def delete_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    ...
```

### 错误处理规范

```python
from fastapi import Request
from fastapi.responses import JSONResponse

@router.exception_handler(BusinessException)
async def business_exception_handler(request: Request, exc: BusinessException):
    return JSONResponse(
        status_code=exc.code,
        content={"code": exc.code, "message": exc.message, "data": None},
    )

# 使用
raise BusinessException(message="文档不存在", code=404)
```

---

## 前端 API 调用规范（TypeScript）

### 统一 request 封装

```typescript
// frontend/src/utils/request.ts
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 30000,
})

// 请求拦截：自动加 JWT token
request.interceptors.request.use((config) => {
  const userStore = useUserStore()
  if (userStore.token) {
    config.headers.Authorization = `Bearer ${userStore.token}`
  }
  return config
})

// 响应拦截：统一错误处理
request.interceptors.response.use(
  (response) => {
    const { code, message, data } = response.data
    if (code !== 200) {
      ElMessage.error(message || '请求失败')
      return Promise.reject(new Error(message))
    }
    return data  // 直接返回 data，减少模板代码
  },
  (error) => {
    if (error.response?.status === 401) {
      // token 过期，跳转登录
      const userStore = useUserStore()
      userStore.logout()
      router.push('/login')
    }
    ElMessage.error(error.message || '网络错误')
    return Promise.reject(error)
  }
)

export default request
```

### API 调用示例

```typescript
// frontend/src/api/document.ts
import request from '@/utils/request'
import type { ApiResponse } from '@/types'

export interface Document {
  id: string
  title: string
  createdAt: string
}

export const documentApi = {
  list: () =>
    request.get<ApiResponse<Document[]>>('/api/documents/list'),

  upload: (file: File, description: string) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('description', description)
    return request.post<ApiResponse>('/api/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  delete: (id: string) =>
    request.delete<ApiResponse>(`/api/documents/${id}`),
}
```

### 流式请求（SSE）规范

```typescript
// frontend/src/utils/sse.ts
export const streamChat = async (
  message: string,
  sessionId: string,
  onChunk: (chunk: string) => void,
) => {
  const eventSource = new EventSource(
    `/api/chat/stream?message=${encodeURIComponent(message)}&session_id=${sessionId}`
  )

  eventSource.onmessage = (event) => {
    if (event.data === '[DONE]') {
      eventSource.close()
      return
    }
    onChunk(event.data)
  }

  eventSource.onerror = (error) => {
    console.error('SSE 错误：', error)
    eventSource.close()
  }

  return eventSource
}
```

---

## 环境变量规范

### 后端（.env）

```bash
# 敏感信息：必须设默认值或留空，禁止硬编码
DASHSCOPE_API_KEY=xxx          # 通义千问 API Key（必需）
SECRET_KEY=xxx                  # JWT 签名密钥（必需）

# 配置项：有合理默认值
LLM_MODEL=qwen-max
LLM_TEMPERATURE=0.7
TOP_K=5
CACHE_TTL_SECONDS=3600
```

### 前端（frontend/.env）

```bash
# 前端环境变量必须以 VITE_ 开头
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_NAME=企业级智能文档问答平台
```

---

## 数据库迁移规范

```bash
# 使用 Alembic（如果启用 MySQL）
uv run alembic init migrations
uv run alembic revision --autogenerate -m "add user table"
uv run alembic upgrade head
```

**禁止**直接修改数据库 schema 而不生成 migration 文件。
