---
description: 项目概述与技术架构，每次对话开始时阅读
alwaysApply: true
---

# Sushi Digital Human - 项目概述

## 项目定位
企业级智能文档问答平台，基于 RAG（Retrieval-Augmented Generation）架构。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + TypeScript + Element Plus + Vite + Pinia |
| 后端 | FastAPI + Python 3.11+ + LangChain 0.3+ |
| LLM | 通义千问 (DashScope) qwen-max |
| 嵌入模型 | Text Embedding V2 (1536 dim) |
| 向量数据库 | ChromaDB 0.5+ |
| 全文检索 | rank-bm25 + jieba |
| 重排序 | BGE-reranker-base |
| 缓存 | Redis 7.0+ |
| 关系数据库 | MySQL (可选，aiomysql + SQLAlchemy async) |
| 包管理 | 后端用 uv，前端用 npm |
| 部署 | Docker Compose / Kubernetes Helm |

## 目录结构（关键路径）

```
backend/
  api/           # FastAPI 路由（chat, documents, auth, agent, alerts, dify, ab_test）
  agent/         # Agent 工具调用逻辑
  chain/         # LangChain 链（rag_chain, summary_chain）
  core/          # 配置与核心服务（config, security, auth_manager, permission_manager, sms_service, dify）
  data_loader/   # 文档加载与分块（loader, chunker, manager, pdf_processor）
  database/      # 数据库模型与会话（models, session）
  generator/     # LLM 生成器（llm.py）
  middleware/     # 中间件
  retrieval/      # 检索模块（hybrid_retriever, vector_store）
  utils/         # 工具函数（logger, performance, rate_limiter, circuit_breaker）
  main.py        # FastAPI 入口

frontend/
  src/
    components/  # Vue 组件
    views/       # 页面视图
    stores/      # Pinia stores
    utils/       # 前端工具
    api/         # API 调用封装

data/
  chroma_db/    # ChromaDB 持久化目录
```

## 启动命令

```bash
# 后端（终端 1）
uv run uvicorn backend.main:app --reload --port 8000

# 前端（终端 2）
cd frontend && cmd /c "npx vite --port 5173"
```

## 关键配置（.env）

```
DASHSCOPE_API_KEY=xxx          # 通义千问 API Key（必需）
LLM_MODEL=qwen-max
EMBEDDING_MODEL=text-embedding-v2
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=xxx                  # JWT 签名密钥
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=7531188
MYSQL_DATABASE=sushi_db
GITHUB_CLIENT_ID=xxx           # GitHub OAuth（可选）
GITHUB_CLIENT_SECRET=xxx
```

## 开发约定

1. **alwaysApply 规则**：项目概述、代码规范、API 约定这三类 rule 设 `alwaysApply: true`，每次对话自动加载
2. **import 顺序**：标准库 → 第三方库 → 项目内部模块，放在文件顶部
3. **类型注解**：所有函数参数和返回值必须有类型注解
4. **命名规范**：Python 用 snake_case，Vue/TS 用 camelCase，组件用 PascalCase
5. **Pinia store**：禁止直接解构，必须通过 store 实例访问
6. **敏感信息**：禁止硬编码，统一用 .env + pydantic-settings 管理
7. **行长度**：Python 120 字符，TS 100 字符
