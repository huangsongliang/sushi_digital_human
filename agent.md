# 企业级智能文档问答平台 Agent 文档

## 📋 概述

企业级智能文档问答平台是一个基于 RAG（检索增强生成）技术的企业级知识库问答系统，帮助企业将分散的文档转化为可查询的智能知识库。

**核心特点：**
- 🤖 **智能问答**：基于文档内容进行精准问答
- 📚 **知识检索**：使用混合检索（BM25 + 向量）和重排序技术
- 💬 **多轮对话**：支持上下文感知的连贯对话
- 🌊 **流式输出**：实时打字机效果的响应体验
- 🔐 **权限管理**：完整的 RBAC 权限体系
- ⚡ **性能优化**：多级缓存、限流熔断

---

## 🏗️ Agent 架构

### 总体架构图

```
用户问题
   ↓
┌──────────────────────────────────────────────────────────────────┐
│                    对话管理器                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │  记忆    │  │  检索器  │  │  生成器  │  │ 权限系统 │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│       │              │              │              │            │
│       └──────────────┼──────────────┼──────────────┘            │
│                      ↓                                        │
│              ┌──────────────┐                                  │
│              │  RAG 链      │                                  │
│              └──────────────┘                                  │
└──────────────────────────────────────────────────────────────────┘
   ↓
流式输出 / 同步响应
```

### 核心组件

#### 1. **记忆系统** ([`backend/memory/`](file:///d:/code/sushi_digital_human/backend/memory/))

| 组件 | 文件 | 功能 |
|------|------|------|
| Redis 客户端 | [`redis_client.py`](file:///d:/code/sushi_digital_human/backend/memory/redis_client.py) | Redis 连接管理 |
| 对话历史 | [`conversation.py`](file:///d:/code/sushi_digital_human/backend/memory/conversation.py) | 会话历史存储与检索 |
| 缓存层 | [`cache.py`](file:///d:/code/sushi_digital_human/backend/memory/cache.py) | 检索结果缓存 |
| 多级缓存 | [`multi_level_cache.py`](file:///d:/code/sushi_digital_human/backend/memory/multi_level_cache.py) | L1+L2 多级缓存 |

#### 2. **检索系统** ([`backend/retrieval/`](file:///d:/code/sushi_digital_human/backend/retrieval/))

| 组件 | 文件 | 功能 |
|------|------|------|
| 混合检索器 | [`hybrid_retriever.py`](file:///d:/code/sushi_digital_human/backend/retrieval/hybrid_retriever.py) | BM25 + 向量 + RRF + 重排序 |
| 向量存储 | [`vector_store.py`](file:///d:/code/sushi_digital_human/backend/retrieval/vector_store.py) | ChromaDB 向量数据库 |

#### 3. **RAG 链** ([`backend/chain/`](file:///d:/code/sushi_digital_human/backend/chain/))

| 组件 | 文件 | 功能 |
|------|------|------|
| RAG 链 | [`rag_chain.py`](file:///d:/code/sushi_digital_human/backend/chain/rag_chain.py) | 完整的 RAG 流程编排 |

#### 4. **提示词系统** ([`backend/prompt/`](file:///d:/code/sushi_digital_human/backend/prompt/))

| 模板 | 用途 |
|------|------|
| `rag_qa` | 单轮 RAG 问答 |
| `multi_turn` | 多轮对话问答 |
| `document_summary` | 文档总结 |
| `question_rewrite` | 问题重写 |

#### 5. **认证授权** ([`backend/core/`](file:///d:/code/sushi_digital_human/backend/core/))

| 组件 | 文件 | 功能 |
|------|------|------|
| 认证管理器 | [`auth_manager.py`](file:///d:/code/sushi_digital_human/backend/core/auth_manager.py) | 用户认证与权限管理 |
| 安全模块 | [`security.py`](file:///d:/code/sushi_digital_human/backend/core/security.py) | JWT 令牌处理 |

---

## 🔍 检索系统详解

### 混合检索流程

```
用户查询
   ↓
┌──────────────┐    ┌──────────────┐
│  BM25 检索   │    │  向量检索    │
│  (关键词)    │    │  (语义)      │
└──────┬───────┘    └──────┬───────┘
       │                   │
       └────────┬──────────┘
                ↓
         ┌──────────────┐
         │  RRF 融合   │
         │  重新排序   │
         └──────┬───────┘
                ↓
         ┌──────────────┐
         │ BGE 重排序   │
         └──────┬───────┘
                ↓
         最终检索结果
```

### 检索配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `TOP_K` | 5 | 检索返回数量 |
| `VECTOR_WEIGHT` | 0.7 | 向量检索权重 |
| `BM25_WEIGHT` | 0.3 | BM25 检索权重 |
| `RERANK_TOP_K` | 3 | 重排序后返回数量 |
| `ENABLE_RERANKING` | true | 是否启用重排序 |

### 核心代码示例

```python
# 获取混合检索器
from backend.retrieval import get_hybrid_retriever
retriever = get_hybrid_retriever()

# 检索相关文档
results = retriever.search(
    query="文档中有关于产品定价的内容吗？",
    top_k=3,
    use_bm25=True,
    use_vector=True,
    use_rerank=True
)
```

---

## 💬 对话系统

### 对话流程

```
1. 用户发送问题
   ↓
2. 验证用户权限
   ↓
3. 检查是否有历史对话
   ↓
4. 检索相关知识
   ↓
5. 构建提示词（包含历史、问题、参考资料）
   ↓
6. 调用 LLM 生成回答
   ↓
7. 流式输出 / 同步返回
   ↓
8. 保存对话历史
```

### 对话历史存储

使用 Redis 存储对话历史，支持：
- 多会话并发处理
- 会话历史持久化
- 自动过期清理（默认 24 小时）

### API 接口

#### 认证接口

```bash
# 用户登录
POST /api/auth/login
{
  "email": "user@example.com",
  "password": "password"
}

# 获取访问令牌
POST /api/auth/refresh
{
  "refresh_token": "your-refresh-token"
}
```

#### 聊天接口（流式）

```bash
POST /api/chat/stream
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "message": "文档中有关于产品定价的内容吗？",
  "session_id": "user123",
  "use_rag": true,
  "top_k": 3
}
```

**响应：** SSE 流式数据

```
data: {"type": "content", "data": "根据文档内容..."}
data: {"type": "references", "data": [...]}
data: [DONE]
```

#### 聊天接口（同步）

```bash
POST /api/chat
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "message": "文档中有关于产品定价的内容吗？",
  "session_id": "user123",
  "use_rag": true
}
```

---

## 📚 文档管理

### 文档管理接口

```bash
# 上传文档
POST /api/documents/upload
Content-Type: multipart/form-data
file: <文件>
description: 文档描述

# 获取文档列表
GET /api/documents/list

# 删除文档
DELETE /api/documents/{document_id}

# 获取文档版本历史
GET /api/documents/{document_id}/versions
```

### 文档处理流程

```
文档上传
   ↓
格式解析 (PDF/Word/TXT/Markdown)
   ↓
智能分块 (基于语义和标题)
   ↓
嵌入生成
   ↓
向量存储
   ↓
索引更新
```

---

## 🎯 提示词工程

### RAG 问答提示词

```python
"""你是一个专业的企业文档问答助手。请根据提供的参考资料回答问题。

【角色设定】
- 你是一个专业、严谨的知识库问答助手
- 回答必须基于提供的参考资料
- 如果参考资料中没有相关信息，请明确说明

【参考资料】
{context}

【问题】
{question}

【回答要求】
1. 必须基于提供的参考资料进行回答
2. 如果参考资料中没有相关信息，请说："文档中未找到相关信息"
3. 用中文清晰、准确地回答问题
4. 不要编造信息
5. 回答要简洁明了

【回答】
"""
```

---

## 🚀 使用指南

### 快速开始

```python
# 1. 获取 RAG 链实例
from backend.chain import get_rag_chain
rag_chain = get_rag_chain()

# 2. 同步调用
result = rag_chain.run(
    query="文档中有关于产品定价的内容吗？",
    top_k=3,
    use_rag=True
)

print(f"回答: {result['answer']}")
print(f"参考资料: {result['references']}")

# 3. 异步调用
result = await rag_chain.async_run(
    query="产品的主要功能有哪些？",
    top_k=3,
    use_rag=True
)

# 4. 流式调用
async for chunk in rag_chain.stream_run(
    query="如何使用这个产品？",
    top_k=3,
    use_rag=True,
    history=history_str
):
    print(chunk, end="")
```

### 添加知识文档

```python
from backend.data_loader.manager import get_document_manager

doc_manager = get_document_manager()

# 上传文档
result = await doc_manager.upload_document(
    file_content="文档内容...",
    file_name="document.md",
    description="产品说明文档"
)
```

---

## ⚙️ 配置选项

### 模型配置

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| LLM 模型 | `LLM_MODEL` | `qwen-max` | 大语言模型 |
| 嵌入模型 | `EMBEDDING_MODEL` | `text-embedding-v2` | 向量嵌入模型 |
| API Key | `DASHSCOPE_API_KEY` | - | 通义千问 API Key |
| 温度 | `LLM_TEMPERATURE` | `0.7` | 生成温度 (0-1) |
| 最大 Token | `LLM_MAX_TOKENS` | `2000` | 单次生成最大 Token 数 |

### 性能配置

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| 缓存 TTL | `CACHE_TTL_SECONDS` | `3600` | 缓存过期时间（秒） |
| 请求限流 | `MAX_REQUESTS_PER_MINUTE` | `1000` | 每分钟最大请求数 |
| 分块大小 | `CHUNK_SIZE` | `512` | 文档分块大小 |
| 分块重叠 | `CHUNK_OVERLAP` | `100` | 分块重叠大小 |

### Redis 配置

| 配置项 | 环境变量 | 默认值 |
|--------|----------|--------|
| Redis URL | `REDIS_URL` | `redis://localhost:6379/0` |
| 最大连接数 | `REDIS_MAX_CONNECTIONS` | `50` |

---

## 🌐 API 端点

### 完整 API 列表

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | `GET` | 系统信息 |
| `/health` | `GET` | 健康检查 |
| `/health/liveness` | `GET` | 存活检查 |
| `/health/readiness` | `GET` | 就绪检查 |
| `/metrics` | `GET` | Prometheus 指标 |
| `/docs` | `GET` | API 文档（Swagger） |
| `/redoc` | `GET` | API 文档（Redoc） |
| `/api/auth/register` | `POST` | 用户注册 |
| `/api/auth/login` | `POST` | 用户登录 |
| `/api/auth/refresh` | `POST` | 刷新令牌 |
| `/api/auth/me` | `GET` | 当前用户信息 |
| `/api/chat` | `POST` | 同步聊天接口 |
| `/api/chat/stream` | `POST` | 流式聊天接口 |
| `/api/documents/upload` | `POST` | 上传文档 |
| `/api/documents/list` | `GET` | 获取文档列表 |
| `/api/documents/{id}` | `DELETE` | 删除文档 |

---

## ⚡ 性能优化

### 多级缓存架构

```
用户请求
    ↓
┌─────────────────────┐
│   L1: 本地内存缓存   │  (LRU, 1000项)
└──────────┬──────────┘
           ↓ (未命中)
┌─────────────────────┐
│   L2: Redis 缓存    │  (分布式, TTL)
└──────────┬──────────┘
           ↓ (未命中)
┌─────────────────────┐
│   L3: 向量数据库    │  (ChromaDB)
└─────────────────────┘
```

### 限流熔断

- **令牌桶限流**：控制请求速率
- **熔断器模式**：服务故障时快速失败
- **并发限制**：控制同时处理的请求数

---

## 📊 监控告警

### 监控指标

| 指标 | 说明 |
|------|------|
| `api_requests_total` | API 请求总数 |
| `api_request_duration_seconds` | 请求耗时分布 |
| `cache_hit_ratio` | 缓存命中率 |
| `error_rate` | 错误率 |
| `active_users` | 活跃用户数 |

### 日志管理

- **Loki**：日志存储与查询
- **Promtail**：日志采集
- **Grafana**：日志可视化

---

## 🐳 生产部署

### Docker Compose 部署

```bash
# 启动生产环境
docker-compose -f docker-compose.prod.yml up -d

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f

# 停止服务
docker-compose -f docker-compose.prod.yml down
```

### Kubernetes Helm 部署

```bash
# 安装 Helm Chart
helm install sushi ./helm --values ./helm/values.yaml

# 查看部署状态
kubectl get pods

# 扩展副本数
helm upgrade sushi ./helm --set backend.replicaCount=5
```

---

## 🔒 安全特性

### 安全措施

| 措施 | 说明 |
|------|------|
| **JWT 认证** | 无状态身份验证 |
| **RBAC 权限** | 基于角色的访问控制 |
| **CORS 配置** | 限制跨域访问 |
| **限流保护** | 防止 API 滥用 |
| **密钥安全** | 使用环境变量存储敏感信息 |
| **主机验证** | 防止 Host 头攻击 |

---

## 📚 参考资料

### 项目文档

- [README.md](file:///d:/code/sushi_digital_human/README.md) - 项目主文档
- [DEPLOYMENT.md](file:///d:/code/sushi_digital_human/DEPLOYMENT.md) - 部署指南

### 技术文档

- [LangChain 文档](https://python.langchain.com/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [ChromaDB 文档](https://docs.trychroma.com/)
- [通义千问 API 文档](https://help.aliyun.com/zh/dashscope/)

---

## 📄 许可证

MIT License
