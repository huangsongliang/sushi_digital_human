# 苏轼文化数字人 Agent 文档

## 📋 概述

苏轼文化数字人 Agent 是一个基于 RAG（检索增强生成）技术的智能对话系统，以北宋著名文学家、书画家苏轼（苏东坡）的身份与用户进行交流。

**核心特点：**
- 🤖 **角色扮演**：完整还原苏轼的性格特点和说话风格
- 📚 **知识检索**：使用混合检索（BM25 + 向量）和重排序技术
- 💬 **多轮对话**：支持上下文感知的连贯对话
- 🌊 **流式输出**：实时打字机效果的响应体验

---

## 🎭 Agent 角色设定

### 角色描述

| 项目 | 详情 |
|------|------|
| **姓名** | 苏轼，字子瞻，号东坡居士 |
| **朝代** | 北宋 |
| **身份** | 文学家、书画家、政治家、唐宋八大家之一 |
| **性格** | 豁达乐观、才华横溢、温文尔雅 |
| **说话风格** | 善用比喻、常引经据典、带文人气息 |
| **擅长领域** | 诗词歌赋、文章书法、人生感悟、美食鉴赏 |

### 核心人格

```
东坡居士形象：
├── 对人生有深刻感悟，善于从日常小事中发现哲理
├── 性情豁达，即使身处逆境也能保持乐观心态
├── 常引用自己的诗词名句，如"但愿人长久，千里共婵娟"
├── 说话温文尔雅，带古代文人气息
└── 可以谈论诗词、书法、绘画、美食、人生等话题
```

---

## 🏗️ Agent 架构

### 总体架构图

```
用户问题
   ↓
┌─────────────────────────────────────────────────────────┐
│                   对话管理器                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │  记忆    │  │  检索器  │  │  生成器  │            │
│  └──────────┘  └──────────┘  └──────────┘            │
│       │              │              │                  │
│       └──────────────┼──────────────┘                  │
│                      ↓                                 │
│              ┌──────────────┐                           │
│              │  RAG 链      │                           │
│              └──────────────┘                           │
└─────────────────────────────────────────────────────────┘
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
    query="苏轼的代表作有哪些？",
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
2. 检查是否有历史对话
   ↓
3. 检索相关知识
   ↓
4. 构建提示词（包含历史、问题、参考资料）
   ↓
5. 调用 LLM 生成回答
   ↓
6. 流式输出 / 同步返回
   ↓
7. 保存对话历史
```

### 对话历史存储

使用 Redis 存储对话历史，支持：
- 多会话并发处理
- 会话历史持久化
- 自动过期清理（默认 24 小时）

### API 接口

#### 聊天接口（流式）

```bash
POST /api/chat/stream
Content-Type: application/json

{
  "message": "你好，东坡居士！",
  "session_id": "user123",
  "use_rag": true,
  "top_k": 3
}
```

**响应：** SSE 流式数据

```
data: {"type": "content", "data": "你好！"}
data: {"type": "content", "data": "我是东坡居士..."}
data: {"type": "references", "data": [...]}
data: [DONE]
```

#### 聊天接口（同步）

```bash
POST /api/chat
Content-Type: application/json

{
  "message": "你好，东坡居士！",
  "session_id": "user123",
  "use_rag": true
}
```

---

## 🎯 提示词工程

### 主要提示词模板

#### RAG 问答提示词

```python
"""你是苏轼（苏东坡），北宋著名文学家、书画家、政治家。请以苏轼的身份和风格回答问题。

【角色设定】
- 你是东坡居士，性情豁达，才华横溢
- 说话风格：温文尔雅，带文人气息，善用比喻，常引经据典
- 对人生有深刻感悟，善于从日常小事中发现哲理
- 可以适当引用自己的诗词名句

【参考资料】
{context}

【问题】
{question}

【回答要求】
1. 必须基于提供的参考资料进行回答
2. 如果参考资料中没有相关信息，请以苏轼的语气说："此事某未详知也"
3. 用中文回答，语言要符合古人说话习惯，但要让现代人能理解
4. 不要编造信息，可以适当发挥文学性表达
5. 回答要有情感，展现苏轼的豁达情怀

【回答】
"""
```

#### 多轮对话提示词

多轮对话版本会增加历史对话内容，保持回答的连贯性。

---

## 🚀 使用指南

### 快速开始

```python
# 1. 获取 RAG 链实例
from backend.chain import get_rag_chain
rag_chain = get_rag_chain()

# 2. 同步调用
result = rag_chain.run(
    query="苏轼的代表作有哪些？",
    top_k=3,
    use_rag=True
)

print(f"回答: {result['answer']}")
print(f"参考资料: {result['references']}")

# 3. 异步调用
result = await rag_chain.async_run(
    query="《水调歌头》表达了什么情感？",
    top_k=3,
    use_rag=True
)

# 4. 流式调用
async for chunk in rag_chain.stream_run(
    query="你是如何看待人生的？",
    top_k=3,
    use_rag=True,
    history=history_str
):
    print(chunk, end="")
```

### 添加知识文档

```python
from backend.retrieval import get_vector_store

vector_store = get_vector_store()

# 添加单篇文档
vector_store.add_documents([
    "苏轼的《水调歌头·明月几时有》是中秋词的代表作..."
])

# 批量添加文档
documents = [
    "文档内容1",
    "文档内容2",
    "文档内容3"
]
vector_store.add_documents(documents)
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

### 检索配置

参见"检索系统详解"章节。

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
| `/docs` | `GET` | API 文档（Swagger） |
| `/redoc` | `GET` | API 文档（Redoc） |
| `/api/chat` | `POST` | 同步聊天接口 |
| `/api/chat/stream` | `POST` | 流式聊天接口 |
| `/api/docs/add` | `POST` | 添加文档 |
| `/api/docs/count` | `GET` | 获取文档数量 |
| `/api/docs` | `DELETE` | 清空所有文档 |

### 详细 API 文档

详见 [Swagger 文档](http://localhost:8000/docs) 或 [README.md](file:///d:/code/sushi_digital_human/README.md)。

---

## 📊 性能特性

### 性能优化措施

| 优化项 | 说明 |
|--------|------|
| **异步处理** | 支持异步检索和异步 LLM 调用 |
| **检索缓存** | Redis 缓存检索结果，提升重复查询速度 |
| **流式输出** | SSE 实时推送，降低首字延迟 |
| **混合检索** | 结合关键词和语义检索，提升准确率 |
| **重排序** | BGE 模型精细化排序，提升相关性 |
| **GZip 压缩** | API 响应压缩，降低传输量 |
| **限流保护** | 防止滥用，保护系统稳定 |

### 性能指标（参考）

| 指标 | 数值 |
|------|------|
| 平均首字延迟 | < 500ms |
| 检索响应时间 | < 200ms |
| 支持并发数 | 100+ |
| 支持文档数 | 100,000+ |

---

## 🧪 测试

### 运行系统集成测试

```bash
# 运行完整集成测试
uv run python tests/test_system_integration.py

# 运行检索模块测试
uv run pytest tests/test_hybrid_retriever.py -v

# 运行向量存储测试
uv run pytest tests/test_vector_store.py -v
```

### 测试用例

详见 [`tests/`](file:///d:/code/sushi_digital_human/tests/) 目录。

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

### 部署架构

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

### 水平扩展

修改 [`docker-compose.prod.yml`](file:///d:/code/sushi_digital_human/docker-compose.prod.yml) 中的 `replicas` 数量来调整 API 实例数：

```yaml
services:
  api:
    deploy:
      replicas: 3  # 修改这里来调整实例数量
```

---

## 🔒 安全特性

### 安全措施

| 措施 | 说明 |
|------|------|
| **CORS 配置** | 限制跨域访问 |
| **限流中间件** | 防止 API 滥用 |
| **并发限制** | 控制最大并发数 |
| **密钥安全** | 使用环境变量存储敏感信息 |
| **主机验证** | 防止 Host 头攻击 |

---

## 📚 参考资料

### 项目文档

- [README.md](file:///d:/code/sushi_digital_human/README.md) - 项目主文档
- [DEPLOYMENT.md](file:///d:/code/sushi_digital_human/DEPLOYMENT.md) - 部署指南
- [docs/ARCHITECTURE_ANALYSIS.md](file:///d:/code/sushi_digital_human/docs/ARCHITECTURE_ANALYSIS.md) - 架构分析
- [docs/PROJECT_SUMMARY.md](file:///d:/code/sushi_digital_human/docs/PROJECT_SUMMARY.md) - 项目总结

### 技术文档

- [LangChain 文档](https://python.langchain.com/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [ChromaDB 文档](https://docs.trychroma.com/)
- [通义千问 API 文档](https://help.aliyun.com/zh/dashscope/)

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

**愿此 Agent 能传承东坡先生的智慧与才情！** 🍵
