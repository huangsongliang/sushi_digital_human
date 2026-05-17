# 苏轼文化数字人问答系统

> 基于 RAG（Retrieval-Augmented Generation）的智能文化知识库问答系统

---

## 📋 项目概述

本项目是一个面向苏轼文化研究的智能问答系统，通过检索增强生成技术（RAG），为用户提供准确、权威的苏轼相关知识问答服务。系统具备多轮对话能力、流式输出、混合检索等核心功能，展现了完整的 AI 应用开发能力。

### 核心特性

- 🗣️ **多轮对话**：基于 Redis 的会话记忆管理，支持上下文感知
- 🌊 **流式输出**：SSE 实时推送，流畅的打字机效果
- 🔍 **混合检索**：BM25 + 向量检索 + RRF 融合 + BGE-reranker 重排序
- 📚 **文档管理**：支持文档添加、查询、删除
- 🎨 **古典界面**：水墨风格的 Vue 3 前端界面
- ⚙️ **配置管理**：灵活的环境配置和参数调节
- 🐳 **生产部署**：支持 Docker Compose 多实例水平扩展 + Nginx 负载均衡

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
| 部署 | Docker + Nginx | - |

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

---

## 📁 项目结构

```
sushi_digital_human/
├── backend/                    # 后端应用
│   ├── api/                   # API 路由
│   │   └── chat.py           # 聊天接口（流式/SSE）
│   ├── chain/                 # RAG 链实现
│   │   └── rag_chain.py      # LangChain LCEL 链式调用
│   ├── core/                  # 核心配置
│   │   ├── config.py         # 环境变量配置
│   │   └── security.py       # 安全认证
│   ├── data_loader/           # 数据加载器
│   │   └── loader.py         # 文档加载
│   ├── generator/             # LLM 封装
│   │   └── llm.py            # DashScope LLM 集成
│   ├── memory/                # 会话记忆
│   │   ├── cache.py          # Redis 缓存
│   │   ├── redis_client.py   # Redis 连接管理
│   │   └── conversation.py   # 对话历史管理
│   ├── models/                # 数据模型
│   │   ├── exceptions.py     # 自定义异常
│   │   └── schemas.py        # Pydantic 模型
│   ├── prompt/                # 提示词模板
│   │   └── templates.py      # 提示词模板定义
│   ├── retrieval/              # 检索模块
│   │   ├── hybrid_retriever.py # 混合检索器
│   │   └── vector_store.py   # ChromaDB 向量存储
│   ├── utils/                 # 工具函数
│   │   ├── logger.py         # 日志工具
│   │   ├── performance.py    # 性能监控
│   │   └── rate_limiter.py   # 限流器
│   └── main.py                # FastAPI 入口
├── frontend/                   # Vue 3 前端
│   ├── src/
│   │   ├── components/       # UI 组件
│   │   │   ├── ChatArea.vue      # 聊天区域
│   │   │   ├── ChatSidebar.vue   # 侧边栏
│   │   │   ├── ReferencePanel.vue # 参考文档
│   │   │   └── SettingsPanel.vue # 设置面板
│   │   ├── stores/           # Pinia 状态管理
│   │   │   └── chat.ts       # 聊天状态
│   │   ├── types/            # TypeScript 类型
│   │   │   └── index.ts      # 类型定义
│   │   ├── App.vue           # 主应用
│   │   └── main.ts           # 入口文件
│   └── package.json
├── config/                     # 配置文件
│   ├── nginx/                 # Nginx 配置
│   │   ├── nginx.conf        # 主配置
│   │   └── conf.d/
│   │       └── upstream.conf # 上游服务配置
│   └── prometheus/            # Prometheus 配置
│       └── prometheus.yml
├── docs/                       # 项目文档
│   ├── 2026-05-15_PROGRESS.md
│   ├── 2026-05-16_PROGRESS.md
│   ├── ARCHITECTURE_ANALYSIS.md
│   ├── DEPLOYMENT_GUIDE.md
│   └── PERFORMANCE_TEST_REPORT.md
├── tests/                      # 测试用例
│   ├── test_system_integration.py  # 系统集成测试
│   ├── test_hybrid_retriever.py    # 检索测试
│   ├── test_vector_store.py         # 向量存储测试
│   └── ... (更多测试文件)
├── Dockerfile                  # Docker 构建文件
├── docker-compose.dev.yml      # 开发环境 Docker 配置
├── docker-compose.prod.yml     # 生产环境 Docker 配置
├── pyproject.toml              # Python 项目配置
├── uv.toml                    # uv 配置
├── requirements.txt            # 依赖列表
└── README.md
```

---

## 🔌 API 接口

### 健康检查

```bash
GET /health

# 响应
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2026-05-17T12:00:00Z"
}
```

### 聊天接口（流式）

```bash
POST /api/chat/stream
Content-Type: application/json

{
  "message": "苏轼的代表作有哪些？",
  "session_id": "user_session_123",
  "use_rag": true,
  "top_k": 3
}
```

**响应**：SSE 流式数据

```
data: {"type": "content", "data": "苏"}
data: {"type": "content", "data": "轼"}
data: {"type": "content", "data": "的"}
...
data: {"type": "references", "data": [...]}
data: [DONE]
```

### 聊天接口（同步）

```bash
POST /api/chat
Content-Type: application/json

{
  "message": "苏轼是谁？",
  "session_id": "user_session_123",
  "use_rag": true,
  "top_k": 3
}
```

**响应**：

```json
{
  "answer": "苏轼（1037年－1101年），字子瞻，号东坡居士...",
  "query": "苏轼是谁？",
  "session_id": "user_session_123",
  "references": [
    {
      "content": "苏轼的代表作包括《水调歌头·明月几时有》...",
      "score": 0.9998,
      "source": "vector_store"
    }
  ]
}
```

### 文档管理

```bash
# 添加文档
POST /api/docs/add
{
  "documents": ["文档内容1", "文档内容2"]
}

# 响应
{
  "status": "success",
  "count": 2
}

# 查询文档数量
GET /api/docs/count

# 响应
{
  "count": 100
}

# 清空文档
DELETE /api/docs

# 响应
{
  "status": "success",
  "deleted_count": 100
}
```

---

## 🧠 核心技术实现

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

### 2. RAG 链流程

```
文档加载 → 文本分块 → 嵌入生成 → 向量存储 → 检索增强 → 提示词构建 → LLM 生成
```

### 3. 流式输出实现

使用 SSE（Server-Sent Events）实现实时响应，前端通过 `EventSource` 接收增量数据。

### 4. 会话记忆

基于 Redis 的会话管理，支持：
- 多会话并行处理
- 会话历史持久化
- 自动过期清理

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

### 数据处理配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `CHUNK_SIZE` | 500 | 文本分块大小 |
| `CHUNK_OVERLAP` | 50 | 分块重叠大小 |

---

## 🐳 生产环境部署

### 使用 Docker Compose 部署

```bash
# 1. 克隆项目
git clone https://github.com/yourusername/sushi_digital_human.git
cd sushi_digital_human

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入您的 API Key

# 3. 构建并启动
docker-compose -f docker-compose.prod.yml up -d

# 4. 查看日志
docker-compose -f docker-compose.prod.yml logs -f
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
                                    │  :8080      │
                                    └──┬───────┬──┘
                                       │       │
                              ┌────────┘       └────────┐
                              ↓                         ↓
                        ┌──────────┐             ┌──────────┐
                        │  API 1   │   ...  ...  │  API N   │
                        │  :8000   │             │  :8000   │
                        └────┬─────┘             └────┬─────┘
                             │                         │
                             └─────────┬───────────────┘
                                       ↓
                               ┌──────────────┐
                               │    Redis     │
                               │   :6379      │
                               └──────────────┘
```

### 扩展说明

- **API 服务**：默认部署 3 个实例，可通过修改 `docker-compose.prod.yml` 中的 `replicas` 调整
- **资源限制**：每个 API 容器限制 1.5 CPU + 1.5G 内存
- **健康检查**：Nginx 会自动跳过不健康的实例

---

## 📝 使用示例

### 问：苏轼是谁？

**答**：苏轼（1037年－1101年），字子瞻，号东坡居士，四川眉山人，北宋著名文学家、书法家、画家，唐宋八大家之一。他的诗词文章风格豪放，书法绘画造诣精深，在中国文学艺术史上占有重要地位。

### 问：苏轼的代表作有哪些？

**答**：苏轼的代表作包括：

1. **词作**：《水调歌头·明月几时有》、《念奴娇·赤壁怀古》、《江城子·密州出猎》等
2. **诗作**：《题西林壁》、《饮湖上初晴后雨》等
3. **散文**：《赤壁赋》、《后赤壁赋》等
4. **书法**：《黄州寒食诗帖》等

### 问：《水调歌头》表达了什么情感？

**答**：《水调歌头·明月几时有》是苏轼在熙宁九年（1076年）中秋之夜创作的，表达了多重情感：

1. **对亲人的思念**：通过对弟弟苏辙的思念，"但愿人长久，千里共婵娟"成为千古名句
2. **对人生的感悟**：融合了儒道佛三家思想，展现了旷达超脱的人生观
3. **对宇宙的思考**：从"明月几时有"的追问，表达了对宇宙人生的深层思考

---

## 🧪 测试

### 运行集成测试

```bash
# 运行系统集成测试
uv run python tests/test_system_integration.py

# 运行检索模块测试
uv run pytest tests/test_hybrid_retriever.py -v

# 运行向量存储测试
uv run pytest tests/test_vector_store.py -v
```

### 测试覆盖

| 模块 | 测试项 | 状态 |
|------|--------|------|
| 混合检索 | BM25 检索 | ✅ |
| 混合检索 | 向量检索 | ✅ |
| 混合检索 | RRF 融合 | ✅ |
| 混合检索 | 重排序 | ✅ |
| RAG 链 | 异步检索 | ✅ |
| RAG 链 | 答案生成 | ✅ |
| 会话记忆 | Redis 连接 | ✅ |
| 会话记忆 | 历史记录 | ✅ |

---

## 🎯 技术亮点

1. **模块化设计**：清晰的代码分层，高内聚低耦合
2. **配置驱动**：灵活的环境变量配置，支持多环境切换
3. **优雅降级**：网络异常时的自动降级机制
4. **类型安全**：完整的 TypeScript 类型定义 + Pydantic 模型
5. **测试覆盖**：完善的单元测试和集成测试
6. **生产就绪**：支持 Docker 部署、Nginx 负载均衡、多实例水平扩展
7. **性能优化**：使用 Hugging Face 镜像源加速模型下载

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交代码 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 发起 Pull Request

---

## 📄 许可证

MIT License

---

## 📧 联系方式

如有问题或建议，欢迎通过 GitHub Issues 联系！

---

*项目已成功部署在 GitHub：[github.com/huangsongliang/sushi_digital_human](https://github.com/huangsongliang/sushi_digital_human)*
