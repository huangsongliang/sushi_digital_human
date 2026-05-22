# 企业级智能文档问答平台

> 基于 RAG（Retrieval-Augmented Generation）的企业级知识库问答系统

---

## 📋 项目概述

本项目是一个企业级智能文档问答平台，通过检索增强生成技术（RAG），帮助企业将分散的文档转化为可查询的智能知识库。系统具备多轮对话、流式输出、混合检索、文档管理、用户权限管理等核心功能，是一个完整的企业级 AI 应用解决方案。

项目实现了从 v1.0 到 v2.0 的全面升级，包括文档处理增强、AI 能力升级、用户体验优化、安全性增强、系统扩展性提升等多个维度的改进。

### 核心特性

- 🤖 **智能 Agent**：支持工具调用、多轮对话、上下文感知的智能助手
- 🗣️ **多轮对话**：基于 Redis 的会话记忆管理，支持上下文感知
- 🌊 **流式输出**：SSE 实时推送，流畅的打字机效果
- 🔍 **混合检索**：BM25 + 向量检索 + RRF 融合 + BGE-reranker 重排序
- 📚 **文档管理**：支持多种格式文档上传、版本管理、权限控制
- 📄 **PDF 处理**：OCR 识别、表格提取、图表解析
- 📝 **智能总结**：支持单文档、多文档、对话总结，多种总结类型
- 🔍 **问答溯源**：完整的推理过程记录，可解释性强
- 🎨 **主题切换**：深色/浅色主题一键切换
- 📱 **响应式设计**：完美适配手机/平板/桌面
- 🔐 **细粒度权限**：RBAC 角色体系 + 文档级权限控制
- 📋 **审计日志**：完整的操作记录、安全事件追踪
- 🚨 **告警系统**：多级别告警、多种通知方式（钉钉/企业微信）
- ⚡ **性能优化**：多级缓存、RAG查询缓存、请求批处理、限流熔断
- 🔌 **插件系统**：模块化设计，支持热插拔扩展
- 🌐 **API 市场**：API 端点注册、密钥管理、访问统计
- 🔗 **应用集成**：钉钉、企业微信、Slack 消息推送
- 📊 **监控告警**：Prometheus + Grafana 监控栈
- 🐳 **生产部署**：支持 Docker Compose、Kubernetes Helm 部署
- 🎨 **现代化界面**：Vue 3 + Element Plus 前端界面

---

## 🛠️ 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 前端框架 | Vue 3 + TypeScript | 3.4+ |
| UI 组件 | Element Plus | 2.8+ |
| 构建工具 | Vite | 5.0+ |
| 状态管理 | Pinia | 2.1+ |
| 后端框架 | FastAPI | 0.115+ |
| Python | Python | 3.11+ |
| AI 框架 | LangChain | 0.3+ |
| 大语言模型 | 通义千问 (DashScope) | qwen-max |
| 嵌入模型 | Text Embedding V2 | - |
| 向量数据库 | ChromaDB | 0.5+ |
| 全文检索 | rank-bm25 + jieba | - |
| 重排序模型 | BGE-reranker-base | - |
| 缓存系统 | Redis | 7.0+ |
| 包管理 | uv | 0.2+ |
| 部署 | Docker + Kubernetes | - |

---

## 🚀 快速开始

### 环境要求

- Python >= 3.11
- uv (Python 包管理工具)
- Redis 7.0+ (用于会话记忆)
- npm >= 10.0+ (前端)

### 1. 安装依赖

```bash
# 后端依赖
uv sync

# 前端依赖
cd frontend
npm install
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并配置 API Key：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# DashScope API Key（阿里云通义千问）
DASHSCOPE_API_KEY=your-api-key-here

# 模型配置
LLM_MODEL=qwen-max
EMBEDDING_MODEL=text-embedding-v2

# Redis 配置（本地开发）
REDIS_URL=redis://localhost:6379/0

# JWT 密钥
SECRET_KEY=your-secret-key-here
```

### 3. 启动服务

```bash
# 启动 Redis（使用 Docker）
docker run -d -p 6379:6379 redis:7-alpine

# 启动后端（终端 1）
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# 启动前端（终端 2）
cd frontend && npm run dev
```

### 4. 访问服务

| 服务 | 地址 |
|------|------|
| 前端界面 | http://localhost:5173 |
| API 文档 | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/health |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 |

---

## 📁 项目结构

```
sushi_digital_human/
├── backend/                    # 后端应用
│   ├── api/                   # API 路由
│   │   ├── chat.py           # 聊天接口（流式/SSE）
│   │   ├── summary.py        # 总结API
│   │   ├── documents.py      # 文档管理接口
│   │   ├── auth.py           # 用户认证接口
│   │   └── ...
│   ├── chain/                 # RAG 链实现
│   │   ├── rag_chain.py      # LangChain LCEL 链式调用
│   │   └── rag_cache.py      # RAG查询缓存
│   ├── core/                  # 核心配置
│   │   ├── config.py         # 环境变量配置
│   │   ├── security.py       # 安全认证
│   │   └── auth_manager.py   # 用户权限管理
│   ├── data_loader/           # 数据加载器
│   │   ├── loader.py         # 文档加载
│   │   ├── chunker.py        # 智能分块器
│   │   └── manager.py        # 文档管理服务
│   ├── database/             # 数据库模型
│   │   ├── models.py         # SQLAlchemy 模型
│   │   ├── session.py        # 数据库会话
│   │   └── pool.py           # 数据库连接池
│   ├── memory/                # 会话记忆
│   │   ├── cache.py          # Redis 缓存
│   │   ├── redis_client.py   # Redis 连接管理
│   │   ├── conversation.py   # 对话历史管理
│   │   └── multi_level_cache.py # 多级缓存
│   ├── middleware/            # 中间件
│   │   └── security.py       # 安全中间件
│   ├── retrieval/             # 检索模块
│   │   ├── hybrid_retriever.py # 混合检索器
│   │   └── vector_store.py   # ChromaDB 向量存储
│   ├── utils/                 # 工具函数
│   │   ├── logger.py         # 日志工具
│   │   ├── performance.py    # 性能监控
│   │   ├── rate_limiter.py   # 限流器
│   │   ├── circuit_breaker.py # 熔断器
│   │   ├── llm_fault_tolerance.py # LLM容错机制
│   │   ├── warnings.py       # 警告过滤器
│   │   └── ...
│   └── main.py                # FastAPI 入口
├── frontend/                   # Vue 3 前端
│   └── src/components/
│       └── ThemeToggle.vue   # 主题切换组件
├── monitoring/                # 监控配置
│   ├── prometheus.yml         # Prometheus配置
│   └── grafana/              # Grafana配置
├── helm/                      # Kubernetes Helm Chart
├── docs/                      # 项目文档
├── tests/                     # 测试用例
│   └── performance/
│       ├── locustfile.py     # Locust性能测试
│       └── benchmark.py      # 基准测试脚本
├── Dockerfile                 # Docker 构建文件
├── docker-compose.monitoring.yml # 监控服务配置
├── pyproject.toml             # Python 项目配置
└── README.md
```

---

## 🔌 API 接口

### 认证接口

```bash
# 用户注册
POST /api/auth/register
{
  "username": "admin",
  "email": "admin@example.com",
  "password": "password123"
}

# 用户登录
POST /api/auth/login
{
  "email": "admin@example.com",
  "password": "password123"
}

# 获取当前用户信息
GET /api/auth/me
Authorization: Bearer <access_token>
```

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

### 聊天接口

```bash
# 流式聊天
POST /api/chat/stream
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "message": "文档中有关于产品定价的内容吗？",
  "session_id": "user_session_123",
  "use_rag": true,
  "top_k": 3
}

# 同步聊天
POST /api/chat
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "message": "文档中有关于产品定价的内容吗？",
  "session_id": "user_session_123",
  "use_rag": true,
  "top_k": 3
}
```

### Agent 接口

```bash
# Agent 对话（支持工具调用）
POST /agent/chat
Content-Type: application/json

{
  "query": "计算 2 + 3 * 4",
  "session_id": "user_session_123"
}

# 获取可用工具列表
GET /agent/tools

# Agent 健康检查
GET /agent/health
```

---

## 🧠 核心技术架构

### 1. 混合检索架构

```
用户查询
    ↓
┌─────────────┬─────────────┐
│  BM25 检索   │  向量检索    │
│  (关键词匹配) │  (语义相似度) │
└──────┬──────┴──────┬──────┘
       ↓              ↓
   Top-K 结果     Top-K 结果
       ↓              ↓
       └──────┬───────┘
              ↓
        RRF 融合排序
       (Reciprocal Rank Fusion)
              ↓
     BGE-reranker 重排序
           (精细化排序)
              ↓
         最终结果
```

### 2. 多级缓存架构

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

### 3. 用户权限体系

```
用户 ──── 拥有 ──── 角色 ──── 拥有 ──── 权限
  │                       │
  │                       └─── 继承 ──── 权限
  │
  └─── 直接分配 ──── 权限
```

---

## 📊 配置选项

### 模型配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `LLM_MODEL` | qwen-max | LLM 模型名称 |
| `EMBEDDING_MODEL` | text-embedding-v2 | 嵌入模型名称 |
| `LLM_TEMPERATURE` | 0.7 | 生成温度 (0-1) |
| `LLM_MAX_TOKENS` | 2000 | 最大 token 数 |

### 检索配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `TOP_K` | 5 | 检索返回数量 |
| `VECTOR_WEIGHT` | 0.7 | 向量检索权重 |
| `BM25_WEIGHT` | 0.3 | BM25 检索权重 |
| `RERANK_TOP_K` | 3 | 重排序返回数量 |
| `ENABLE_RERANKING` | true | 是否启用重排序 |

### 性能配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `MAX_REQUESTS_PER_MINUTE` | 1000 | 每分钟最大请求数 |
| `CACHE_TTL_SECONDS` | 3600 | 缓存过期时间（秒） |
| `CHUNK_SIZE` | 512 | 文本分块大小 |
| `CHUNK_OVERLAP` | 100 | 分块重叠大小 |

---

## 🐳 生产环境部署

### 使用 Docker Compose 部署

```bash
# 1. 克隆项目
git clone https://github.com/huangsongliang/sushi_digital_human.git
cd sushi_digital_human

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入您的 API Key

# 3. 构建并启动
docker-compose -f docker-compose.prod.yml up -d

# 4. 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

### 使用 Kubernetes Helm 部署

```bash
# 安装 Helm Chart
helm install sushi ./helm --values ./helm/values.yaml

# 查看部署状态
kubectl get pods

# 扩展副本数
helm upgrade sushi ./helm --set backend.replicaCount=5
```

### 启动监控服务

```bash
# 使用 Docker Compose 启动 Prometheus + Grafana
docker-compose -f docker-compose.monitoring.yml up -d

# 访问 Grafana (默认账号密码: admin/admin)
# 浏览器打开 http://localhost:3001
```

### 架构说明

```
                                    ┌─────────────┐
                                    │   前端      │
                                    │  (Vue 3)    │
                                    └──────┬──────┘
                                           │
                                    ┌──────▼──────┐
                                    │   Nginx     │
                                    │  (负载均衡)  │
                                    └──┬───────┬──┘
                                       │       │
                              ┌────────┘       └────────┐
                              ↓                         ↓
                        ┌──────────┐             ┌──────────┐
                        │  API 1   │   ...  ...  │  API N   │
                        └────┬─────┘             └────┬─────┘
                             │                         │
                             └─────────┬───────────────┘
                                       ↓
                              ┌──────────────┐
                              │    Redis     │
                              └──────────────┘
```

---

## 📈 监控与告警

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

## 🎯 企业级特性

### 1. 智能 Agent 能力
- 🤖 **工具调用**：支持 RAG 知识库问答、计算器、总结等工具
- 💬 **多轮对话**：基于 Redis 的会话记忆，支持上下文保持
- 🧠 **智能决策**：自动分析问题并选择合适的工具

### 2. 文档处理能力
- 📄 **PDF OCR**：支持扫描件识别，中英文混合识别
- 📊 **表格提取**：Camelot + pdfplumber 双引擎提取
- 📋 **图表解析**：支持表格转 Markdown 格式

### 3. 智能总结能力
- 📝 **多类型总结**：简短、详细、要点、结构化、极简总结
- 📚 **多文档总结**：支持合并多个文档进行综合总结
- 💬 **对话总结**：自动总结对话历史内容

### 4. 可解释性
- 🔍 **问答溯源**：完整记录推理过程和检索来源
- 📚 **引用显示**：展示回答的参考文档和相似度评分
- 🧠 **推理路径**：可视化展示思考过程

### 5. 权限管理
- 🔐 **RBAC 角色体系**：admin、editor、viewer 默认角色
- 📄 **文档级权限**：支持细粒度的文档访问控制
- 🛡️ **权限装饰器**：FastAPI 集成的权限验证

### 6. 安全审计
- 📋 **审计日志**：完整的操作记录和安全事件追踪
- 🔍 **用户活动追踪**：记录用户的所有关键操作
- 🚨 **安全事件告警**：异常登录、权限变更等安全事件

### 7. 告警系统
- 📊 **多级别告警**：CRITICAL、ERROR、WARNING、INFO
- 🔔 **多渠道通知**：钉钉、企业微信、Webhook、邮件
- ⏱️ **告警抑制**：支持冷却时间和静默机制

### 8. 插件系统
- 🔌 **模块化设计**：支持热插拔扩展
- 🧩 **多种插件类型**：检索器、生成器、处理器、认证等
- 📦 **生命周期管理**：初始化、运行、关闭、健康检查

### 9. API 市场
- 🌐 **API 注册**：标准化的端点注册和发现
- 🔑 **密钥管理**：API Key 创建、验证、撤销
- 📈 **访问统计**：调用次数、成功率、延迟统计

### 10. 应用集成
- 🔗 **钉钉集成**：支持文本、Markdown、链接、卡片消息
- 💼 **企业微信集成**：支持多种消息类型
- 💬 **Slack 集成**：团队协作消息推送

### 11. 高可用与性能
- 📦 **多实例部署**：支持自动扩缩容、故障转移
- ⚡ **多级缓存**：内存缓存 + Redis + 向量数据库
- 🔒 **限流熔断**：防止系统过载

### 12. 可观测性
- 📊 **监控指标**：Prometheus 集成的全面指标
- 📝 **日志管理**：Loki + Promtail + Grafana
- 🔍 **链路追踪**：完整的请求链路追踪

---

## 📄 许可证

MIT License

---

## 📧 联系方式

如有问题或建议，欢迎通过 GitHub Issues 联系！

---

*项目地址：[github.com/huangsongliang/sushi_digital_human](https://github.com/huangsongliang/sushi_digital_human)*
