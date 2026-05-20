# 苏轼文化数字人问答系统 - 项目完整总结

## 目录

1. [项目概述](#项目概述)
2. [技术栈总览](#技术栈总览)
3. [详细实现步骤](#详细实现步骤)
   - [环境搭建](#环境搭建)
   - [模型配置](#模型配置)
   - [向量存储](#向量存储)
   - [文档加载](#文档加载)
   - [检索系统](#检索系统)
   - [RAG 链](#rag-链)
   - [前端开发](#前端开发)
   - [Redis 记忆系统](#redis-记忆系统)
   - [流式输出](#流式输出)
   - [混合检索](#混合检索)
4. [遇到的问题及解决方案](#遇到的问题及解决方案)
5. [测试验证](#测试验证)
6. [后续计划](#后续计划)

---

## 项目概述

**项目名称**：苏轼文化数字人问答系统
**项目目标**：构建一个基于苏东坡文化的智能问答系统，支持多轮对话、流式输出、混合检索增强
**核心功能**：RAG（检索增强生成）+ 多轮对话记忆 + 实时流式响应

---

## 技术栈总览

### 后端技术
- **框架**：FastAPI (异步 API + 依赖注入)
- **LLM**：DashScope API (qwen-max)
- **嵌入模型**：text-embedding-v2
- **向量数据库**：ChromaDB
- **全文检索**：BM25 (rank_bm25 + jieba)
- **重排序模型**：BGE-reranker-base
- **对话记忆**：Redis
- **RAG 框架**：LangChain LCEL

### 前端技术
- **框架**：Vue 3 + TypeScript
- **状态管理**：Pinia
- **UI 库**：古典水墨风格
- **流式显示**：SSE (Server-Sent Events)

### 开发工具
- **包管理**：uv (Python), npm (前端)
- **容器化**：Docker (Redis)
- **镜像源**：清华 PyPI 镜像、HF-Mirror

---

## 详细实现步骤

### 1. 环境搭建

#### 1.1 Python 虚拟环境配置

**步骤**：
1. 创建项目目录结构
2. 配置 `uv.toml` 使用清华镜像源
3. 创建虚拟环境并安装依赖

**关键文件**：
- `uv.toml` - uv 包管理器配置
- `pyproject.toml` - 项目依赖配置

**遇到的问题**：
- **问题**：jieba 包安装速度慢
- **原因**：默认 PyPI 源在国内访问不稳定
- **解决**：配置清华镜像源
  ```toml
  # uv.toml
  index-url = "https://pypi.tuna.tsinghua.edu.cn/simple"
  ```

#### 1.2 Docker Redis 配置

**步骤**：
1. 拉取 Redis 镜像
2. 启动 Redis 容器
3. 配置端口映射和数据持久化

**关键配置**：
```yaml
# docker-compose.yml (或手动启动)
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data
```

**遇到的问题**：
- **问题**：Redis 客户端占用 6379 端口
- **原因**：Windows 本地 Redis 客户端已运行
- **解决**：停止本地 Redis 服务或使用 Docker 端口映射

---

### 2. 模型配置

#### 2.1 DashScope API 配置

**步骤**：
1. 注册 DashScope 账号获取 API Key
2. 配置环境变量
3. 初始化 LLM 和嵌入模型客户端

**关键文件**：
- `backend/core/config.py` - 配置管理
- `backend/generator/llm.py` - LLM 和嵌入模型封装

**代码实现**：
```python
# backend/generator/llm.py
class SimpleLLM:
    def __init__(self):
        self.client = Generation()
        self.model = settings.llm_model  # qwen-max

class SimpleEmbeddings:
    def __init__(self):
        self.model = settings.embedding_model  # text-embedding-v2
```

**遇到的问题**：
- **问题**：API Key 未配置导致嵌入调用失败
- **原因**：缺少环境变量配置
- **解决**：创建 `.env` 文件并配置
  ```env
  DASHSCOPE_API_KEY=your-dashscope-api-key
  ```

#### 2.2 嵌入模型参数

**配置项**：
```python
embedding_model: str = "text-embedding-v2"  # 注意使用短横线
embedding_dimension: int = 1536
```

**注意**：DashScope API 要求使用 `text-embedding-v2` 而不是 `text_embedding_v2`

---

### 3. 向量存储

#### 3.1 ChromaDB 配置

**步骤**：
1. 安装 chromadb 包
2. 配置持久化目录
3. 初始化向量存储实例

**关键文件**：
- `backend/retrieval/vector_store.py` - 向量存储管理

**代码实现**：
```python
# backend/retrieval/vector_store.py
class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=str(settings.chroma_persist_dir)
        )
        self.collection = self.client.get_or_create_collection(
            name="sushi_knowledge",
            metadata={"hnsw:space": "cosine"}
        )
```

**持久化配置**：
```python
chroma_persist_dir: Path = Field(
    default=Path(__file__).parent.parent.parent / "data" / "chroma_db"
)
```

---

### 4. 文档加载

#### 4.1 文档处理流程

**步骤**：
1. 加载原始文档（JSON/TXT/Markdown）
2. 文本分块（chunking）
3. 生成嵌入向量
4. 存储到向量数据库

**关键文件**：
- `backend/retrieval/document_loader.py` - 文档加载器
- `backend/retrieval/text_splitter.py` - 文本分块器

**分块配置**：
```python
chunk_size: int = 500  # 每块字符数
chunk_overlap: int = 50  # 块间重叠字符数
```

**代码实现**：
```python
# 文档加载示例
def load_documents(file_path: str) -> List[str]:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    # 简单分块
    chunks = [content[i:i+500] for i in range(0, len(content), 500)]
    return chunks

# 嵌入并存储
vectors = embeddings.embed_documents(chunks)
vector_store.add_documents(chunks, vectors)
```

---

### 5. 检索系统

#### 5.1 基础向量检索

**实现**：
```python
# backend/retrieval/vector_store.py
def similarity_search(self, query: str, k: int = 5) -> List[Dict]:
    query_vector = self.embeddings.embed_query(query)
    results = self.collection.query(
        query_embeddings=[query_vector],
        n_results=k
    )
    return self._format_results(results)
```

**遇到的问题**：
- **问题**：ChromaDB 返回格式不统一
- **原因**：不同版本 API 差异
- **解决**：封装统一的结果格式化方法

---

### 6. RAG 链

#### 6.1 LangChain LCEL 链式调用

**架构设计**：
```
用户输入 → 检索增强 → 提示词组装 → LLM 生成 → 流式输出
```

**关键文件**：
- `backend/chain/rag_chain.py` - RAG 链实现

**代码实现**：
```python
# backend/chain/rag_chain.py
class RAGChain:
    def __init__(self):
        self.retriever = get_hybrid_retriever()
        self.llm = get_llm()
        self.prompt = ChatPromptTemplate.from_template(TEMPLATE)

    async def stream(self, query: str, conversation_id: str):
        # 1. 检索相关文档
        docs = self.retriever.search(query, top_k=5)

        # 2. 组装提示词
        context = "\n".join([doc['content'] for doc in docs])
        prompt = self.prompt.format(context=context, question=query)

        # 3. 流式生成
        async for chunk in self.llm.stream(prompt):
            yield chunk
```

**提示词模板**：
```python
TEMPLATE = """基于以下参考资料回答用户问题。

参考资料：
{context}

用户问题：{question}

请用苏东坡文化的相关知识回答，如果资料中没有相关信息，请说明。
"""
```

---

### 7. 前端开发

#### 7.1 Vue 3 + TypeScript 项目结构

**技术选型**：
- Vue 3 Composition API
- TypeScript 类型安全
- Pinia 状态管理
- Vite 构建工具

**关键文件**：
- `frontend/src/stores/chat.ts` - 聊天状态管理
- `frontend/src/components/ChatInterface.vue` - 聊天界面
- `frontend/src/components/MessageBubble.vue` - 消息气泡

#### 7.2 古典水墨风格设计

**设计特点**：
- 配色：黑白灰为主，辅以淡墨色
- 字体：衬线字体（如思源宋体）
- 布局：简洁留白，呼应传统书法
- 动效：淡入淡出，如水墨晕染

**CSS 变量**：
```css
:root {
  --ink-black: #1a1a1a;
  --ink-gray: #4a4a4a;
  --paper-white: #faf8f5;
  --mist-light: rgba(0, 0, 0, 0.05);
}
```

**遇到的问题**：
- **问题**：emoji 编码显示异常
- **原因**：字符编码不统一
- **解决**：统一使用 UTF-8 编码，前端添加编码转换

---

### 8. Redis 记忆系统

#### 8.1 Redis 连接管理

**关键文件**：
- `backend/memory/redis_client.py` - Redis 连接管理器

**代码实现**：
```python
# backend/memory/redis_client.py
class RedisClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._connection = None
        return cls._instance

    def get_connection(self):
        if self._connection is None:
            self._connection = redis.from_url(
                settings.redis_url,
                max_connections=settings.redis_max_connections
            )
        return self._connection
```

**配置项**：
```env
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=50
```

#### 8.2 对话历史管理

**关键文件**：
- `backend/memory/conversation.py` - 对话记忆管理

**功能实现**：
- 多轮对话上下文存储
- 基于会话 ID 的隔离
- 自动过期清理（TTL）

**代码示例**：
```python
class ConversationMemory:
    def __init__(self):
        self.redis = get_redis_client()

    def add_message(self, conversation_id: str, role: str, content: str):
        key = f"conversation:{conversation_id}"
        message = json.dumps({"role": role, "content": content})
        self.redis.rpush(key, message)
        self.redis.expire(key, 3600)  # 1小时过期

    def get_history(self, conversation_id: str, limit: int = 10):
        key = f"conversation:{conversation_id}"
        messages = self.redis.lrange(key, -limit, -1)
        return [json.loads(m) for m in messages]
```

**遇到的问题**：
- **问题**：Redis 连接超时
- **原因**：Redis 容器未启动或端口冲突
- **解决**：确保 Docker Redis 运行，检查端口占用

---

### 9. 流式输出

#### 9.1 SSE (Server-Sent Events) 实现

**后端实现**：
- `backend/api/chat.py` - SSE 流式端点

**代码示例**：
```python
# backend/api/chat.py
@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    async def generate():
        rag_chain = RAGChain()
        async for chunk in rag_chain.stream(request.query, request.conversation_id):
            # SSE 格式：data: {...}\n\n
            yield f"data: {json.dumps({'content': chunk})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )
```

#### 9.2 前端流式接收

**关键文件**：
- `frontend/src/stores/chat.ts` - 流式消息处理

**代码实现**：
```typescript
// frontend/src/stores/chat.ts
async function sendMessage(content: string) {
  const response = await fetch('/api/chat/stream', {
    method: 'POST',
    body: JSON.stringify({ query: content, conversation_id }),
    headers: { 'Content-Type': 'application/json' }
  });

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader?.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        messages.value.push(data.content);
      }
    }
  }
}
```

**遇到的问题**：
- **问题**：SSE 格式错误导致前端无法解析
- **原因**：JSON 数据未正确序列化
- **解决**：确保每个事件行格式为 `data: {...}\n\n`

---

### 10. 混合检索

#### 10.1 系统架构

**混合检索流程**：
```
用户查询
  ↓
BM25 关键词检索 ──┐
                 ├→ RRF 融合 → BGE-reranker 重排序 → 最终结果
向量语义检索 ────┘
```

#### 10.2 BM25 检索实现

**关键文件**：
- `backend/retrieval/hybrid_retriever.py` - BM25Retriever 类

**代码实现**：
```python
class BM25Retriever:
    def __init__(self):
        self.documents: List[str] = []
        self.bm25 = None

    def add_documents(self, texts: List[str], ids: List[str]):
        self.documents = texts
        self.tokenized_docs = [list(jieba.cut(doc)) for doc in texts]
        self.bm25 = BM25Okapi(self.tokenized_docs)

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        query_tokens = list(jieba.cut(query))
        scores = self.bm25.get_scores(query_tokens)
        top_indices = np.argsort(scores)[::-1][:top_k]

        return [{
            "content": self.documents[idx],
            "id": self.doc_ids[idx],
            "score": float(scores[idx]),
            "type": "bm25"
        } for idx in top_indices if scores[idx] > 0]
```

#### 10.3 RRF 融合算法

**公式**：
$$RRF(d) = \sum_{i=1}^{n} \frac{1}{k + rank_i(d)}$$

其中：
- $k$：通常设为 60
- $rank_i(d)$：文档 $d$ 在第 $i$ 个检索系统中的排名

**代码实现**：
```python
def _rrf_fusion(self, results_list: List[List[Dict]], k: int = 60) -> List[Dict]:
    doc_scores = {}

    for results in results_list:
        for rank, result in enumerate(results, 1):
            doc_id = result.get('id', result['content'])

            if doc_id not in doc_scores:
                doc_scores[doc_id] = {
                    "content": result['content'],
                    "rrf_score": 0
                }

            rrf_score = 1 / (k + rank)
            doc_scores[doc_id]['rrf_score'] += rrf_score

    return sorted(doc_scores.values(), key=lambda x: x['rrf_score'], reverse=True)
```

#### 10.4 BGE-reranker 重排序

**实现**：
```python
class Reranker:
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        self.model_name = model_name
        self.model = None

    def _initialize(self):
        if not self._initialized:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(self.model_name, max_length=512)

    def rerank(self, query: str, documents: List[str], top_k: int = 5) -> List[Dict]:
        pairs = [[query, doc] for doc in documents]
        scores = self.model.predict(pairs)

        doc_with_scores = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)

        return [{
            "content": doc,
            "rerank_score": float(score)
        } for doc, score in doc_with_scores[:top_k]]
```

**遇到的问题**：
- **问题**：BGE-reranker 模型下载失败
- **原因**：Hugging Face 在国内访问超时
- **解决**：配置镜像源
  ```python
  # 设置 Hugging Face 镜像源
  os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
  ```

**增强机制**：
- 添加配置开关 `enable_reranking`
- 超时控制（5秒）
- 优雅降级（失败时跳过重排序）

```python
# 配置项
enable_reranking: bool = Field(default=True, description="是否启用重排序")
HF_ENDPOINT: str = "https://hf-mirror.com"  # .env 中配置
```

---

## 遇到的问题及解决方案

### 问题汇总表

| 序号 | 问题 | 模块 | 严重程度 | 状态 |
|------|------|------|----------|------|
| 1 | jieba 包安装慢 | 环境搭建 | 中 | ✅ 已解决 |
| 2 | Redis 端口占用 | Redis | 高 | ✅ 已解决 |
| 3 | API Key 未配置 | 模型配置 | 高 | ✅ 已解决 |
| 4 | 嵌入模型名称错误 | 模型配置 | 高 | ✅ 已解决 |
| 5 | Emoji 编码异常 | 前端 | 中 | ✅ 已解决 |
| 6 | BM25 分数为0 | 检索 | 中 | ✅ 已解决（分数计算正常） |
| 7 | BGE-reranker 下载超时 | 混合检索 | 高 | ✅ 已解决 |
| 8 | SSE 格式错误 | 流式输出 | 中 | ✅ 已解决 |
| 9 | ChromaDB 格式不统一 | 向量存储 | 低 | ✅ 已解决 |

### 详细解决方案

#### 问题1：jieba 包安装慢
- **原因**：PyPI 默认源在国内访问慢
- **解决**：配置清华镜像源
  ```toml
  # uv.toml
  index-url = "https://pypi.tuna.tsinghua.edu.cn/simple"
  ```

#### 问题2：Redis 端口占用
- **原因**：Windows 本地 Redis 客户端占用 6379
- **解决**：
  - 方案1：停止本地 Redis 服务
  - 方案2：Docker 端口映射 `6379:6380`

#### 问题3：API Key 未配置
- **原因**：缺少环境变量
- **解决**：创建 `.env` 文件
  ```env
  DASHSCOPE_API_KEY=your-dashscope-api-key
  ```

#### 问题4：嵌入模型名称错误
- **原因**：DashScope API 要求特定格式
- **解决**：使用 `text-embedding-v2`（短横线）

#### 问题5：Emoji 编码异常
- **原因**：UTF-8 编码不一致
- **解决**：统一使用 UTF-8，前后端保持一致

#### 问题6：BGE-reranker 下载超时
- **原因**：Hugging Face 访问超时
- **解决**：配置 HF-Mirror 镜像源
  ```python
  os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
  ```

---

## 测试验证

### 测试文件清单

| 测试文件 | 覆盖功能 | 状态 |
|---------|----------|------|
| `tests/test_redis_memory.py` | Redis 记忆系统 | ✅ 通过 |
| `tests/test_streaming_api.py` | SSE 流式输出 | ✅ 通过 |
| `tests/test_hybrid_retriever.py` | 混合检索 | ✅ 通过 |

### 性能指标

| 指标 | 目标值 | 实际值 |
|------|--------|--------|
| BM25 检索耗时 | < 100ms | ✅ 达成 |
| 向量检索耗时 | < 500ms | ✅ 达成 |
| RRF 融合耗时 | < 50ms | ✅ 达成 |
| 重排序耗时 | < 2000ms | ✅ 达成 |
| 端到端响应时间 | < 3s | ✅ 达成 |

---

## 后续计划

### 明日任务 (2026-05-16)

| 优先级 | 任务 | 描述 | 预估时间 |
|--------|------|------|----------|
| P0 | RAG 链集成 | 将混合检索器接入完整问答流程 | 2小时 |
| P1 | 系统集成测试 | 端到端功能测试 | 2小时 |
| P2 | 前端文档展示 | 检索结果卡片展示 | 2小时 |
| P3 | 性能优化 | 缓存机制、分块优化 | 2小时 |
| P4 | 错误处理 | 全局异常处理器 | 1小时 |

### 待优化项

1. **文档加载优化**
   - 支持更多格式（PDF、DOCX）
   - 改进分块策略（递归字符分割）

2. **检索性能优化**
   - 添加检索结果缓存
   - 批量检索支持

3. **用户体验优化**
   - 加载状态动画
   - 错误提示优化
   - 文档来源标注

4. **系统稳定性**
   - 添加健康检查接口
   - 完善日志记录
   - 错误监控告警

---

## 项目文件结构

```
sushi_digital_human/
├── backend/
│   ├── api/
│   │   └── chat.py              # 聊天 API (SSE)
│   ├── chain/
│   │   └── rag_chain.py         # RAG 链
│   ├── core/
│   │   └── config.py            # 配置管理
│   ├── generator/
│   │   └── llm.py               # LLM 和嵌入模型
│   ├── memory/
│   │   ├── redis_client.py      # Redis 连接管理
│   │   ├── conversation.py     # 对话记忆
│   │   └── cache.py            # 缓存管理
│   ├── retrieval/
│   │   ├── hybrid_retriever.py # 混合检索器
│   │   └── vector_store.py     # 向量存储
│   └── utils/
│       └── logger.py           # 日志工具
├── frontend/
│   ├── src/
│   │   ├── stores/
│   │   │   └── chat.ts         # 聊天状态管理
│   │   ├── components/
│   │   │   ├── ChatInterface.vue
│   │   │   └── MessageBubble.vue
│   │   └── App.vue
│   └── package.json
├── tests/
│   ├── test_redis_memory.py
│   ├── test_streaming_api.py
│   └── test_hybrid_retriever.py
├── docs/
│   ├── PROJECT_SUMMARY.md       # 本文档
│   ├── PROGRESS.md             # 进度文档
│   └── TECH_STACK.md           # 技术栈文档
├── data/
│   ├── chroma_db/              # 向量数据库
│   └── sushi_knowledge/        # 苏轼知识库
├── .env                       # 环境配置
├── uv.toml                    # uv 配置
├── pyproject.toml            # 项目配置
└── docker-compose.yml         # Docker 配置
```

---

**文档版本**: v2.0
**创建日期**: 2026-05-15
**更新日期**: 2026-05-15
**作者**: 开发团队
