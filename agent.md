# 企业级智能文档问答平台 Agent 模块

## 🤖 Agent 概述

Agent 模块是基于 LangChain 的智能助手系统，支持**工具调用**、**多轮对话上下文保持**和**智能决策**。通过 Agent，您可以构建更加智能的问答系统，自动选择合适的工具来解决用户问题。

**核心特性：**

- 🔧 **工具调用**：支持 RAG 知识库问答、计算器、总结等工具
- 💬 **多轮对话**：基于 Redis 的会话记忆管理
- 🧠 **智能决策**：自动分析问题并选择合适的工具
- 🔄 **上下文感知**：理解对话历史并保持一致性

---

## 🏗️ Agent 架构

### 总体架构图

```
用户查询
   ↓
┌──────────────────────────────────────────────────────────────┐
│                     Agent 管理器                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  工具注册表  │  LLM 决策中心  │  对话记忆系统      │   │
│  └─────────────┼────────────────┼──────────────────────┘   │
│                ↓                ↓                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                    工具执行引擎                       │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │   │
│  │  │ RAG工具  │  │ 计算器   │  │  总结器  │  ...     │   │
│  │  └──────────┘  └──────────┘  └──────────┘          │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
   ↓
智能回答（直接回答或工具调用结果）
```

### 核心组件

| 组件 | 文件 | 功能 |
|------|------|------|
| Agent 管理器 | [`backend/agent/__init__.py`](file:///d:/code/sushi_digital_human/backend/agent/__init__.py) | Agent 核心逻辑、工具调度 |
| Agent API | [`backend/api/agent.py`](file:///d:/code/sushi_digital_human/backend/api/agent.py) | Agent 对外 API 端点 |
| RAG 工具 | `DocumentQATool` | 基于知识库的问答 |
| 计算器工具 | `CalculatorTool` | 数学计算 |
| 总结工具 | `SummaryTool` | 文本总结 |
| 对话记忆 | [`backend/memory/conversation.py`](file:///d:/code/sushi_digital_human/backend/memory/conversation.py) | Redis 会话存储 |

---

## 🔧 工具系统

### 可用工具列表

| 工具名称 | 标识 | 描述 |
|----------|------|------|
| RAG 知识库问答 | `document_qa` | 回答关于文档知识库的问题 |
| 计算器 | `calculator` | 执行数学计算 |
| 总结器 | `summarize` | 总结对话内容或长文本 |

### 工具调用流程

```
1. 用户提问
   ↓
2. Agent 分析问题
   ↓
3. 决定是否调用工具
   ├── 是 → 选择工具 → 执行工具 → 返回结果
   └── 否 → 直接回答
   ↓
4. 保存对话历史
```

---

## 💬 Agent API 接口

### Agent 对话接口

**请求：**

```bash
POST /agent/chat
Content-Type: application/json

{
  "query": "文档中关于产品定价的内容有哪些？",
  "session_id": "user_session_123"
}
```

**参数说明：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query` | string | 是 | 用户查询内容 |
| `session_id` | string | 否 | 会话 ID，用于保持多轮对话上下文 |

**响应：**

```json
{
  "answer": "根据文档内容，产品定价策略如下：...",
  "sources": [],
  "thought": "使用工具 document_qa 完成查询",
  "tool_used": "document_qa"
}
```

**响应字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `answer` | string | 回答内容 |
| `sources` | array | 参考资料列表 |
| `thought` | string | Agent 的思考过程 |
| `tool_used` | string | 使用的工具名称（null 表示直接回答） |

### 获取工具列表

**请求：**

```bash
GET /agent/tools
```

**响应：**

```json
[
  {
    "name": "document_qa",
    "description": "用于回答关于文档知识库的问题，包括企业文档、政策文件、产品手册、技术文档等内容。"
  },
  {
    "name": "calculator",
    "description": "用于执行数学计算，包括加减乘除、幂运算、平方根等。"
  },
  {
    "name": "summarize",
    "description": "用于总结对话内容或长文本。"
  }
]
```

### Agent 健康检查

**请求：**

```bash
GET /agent/health
```

**响应：**

```json
{
  "status": "healthy",
  "tools_count": 3
}
```

---

## 🔄 多轮对话

### 上下文保持机制

Agent 使用 Redis 存储对话历史，支持跨请求的上下文保持：

```python
# 第一轮对话
POST /agent/chat
{
  "query": "我想了解产品定价",
  "session_id": "user_123"
}

# 第二轮对话（自动关联上下文）
POST /agent/chat
{
  "query": "它有什么优惠活动吗？",
  "session_id": "user_123"
}
```

### 对话历史存储

| 属性 | 说明 |
|------|------|
| 存储位置 | Redis |
| 过期时间 | 24 小时 |
| 消息格式 | role + content |
| 支持并发 | 是 |

---

## 🚀 使用示例

### 示例 1：直接回答

**请求：**

```bash
curl -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "你好，很高兴认识你"
  }'
```

**响应：**

```json
{
  "answer": "你好！很高兴认识你！我是你的智能助手，有什么可以帮助你的吗？",
  "sources": [],
  "thought": "直接回答用户问题",
  "tool_used": null
}
```

### 示例 2：调用计算器工具

**请求：**

```bash
curl -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "计算 2 + 3 * 4"
  }'
```

**响应：**

```json
{
  "answer": "2 + 3 * 4 = 14",
  "sources": [],
  "thought": "使用工具 calculator 完成查询",
  "tool_used": "calculator"
}
```

### 示例 3：调用 RAG 工具

**请求：**

```bash
curl -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "文档中有关于产品定价的内容吗？",
    "session_id": "session_001"
  }'
```

**响应：**

```json
{
  "answer": "根据知识库内容，产品定价策略如下：...",
  "sources": [...],
  "thought": "使用工具 document_qa 完成查询",
  "tool_used": "document_qa"
}
```

---

## 🧩 扩展工具

### 添加新工具

要添加自定义工具，只需在 `backend/agent/__init__.py` 中添加新的工具类：

```python
class CustomTool:
    """自定义工具示例"""
    
    name = "custom_tool"
    description = "自定义工具描述"
    
    def run(self, parameter: str) -> str:
        """工具执行逻辑"""
        return f"处理结果: {parameter}"
```

然后在 `_initialize_tools` 方法中注册：

```python
def _initialize_tools(self) -> List[Tool]:
    tools = []
    
    # 添加自定义工具
    custom_tool = CustomTool()
    tools.append(Tool(
        name=custom_tool.name,
        func=custom_tool.run,
        description=custom_tool.description
    ))
    
    return tools
```

---

## 🔗 与现有系统集成

### Agent vs 传统聊天接口

| 特性 | `/agent/chat` | `/api/chat` |
|------|---------------|-------------|
| 工具调用 | ✅ 支持 | ❌ 不支持 |
| 多轮对话 | ✅ 支持 | ✅ 支持 |
| RAG 检索 | ✅ 通过工具 | ✅ 直接支持 |
| 智能决策 | ✅ 自动选择工具 | ❌ 手动配置 |

### 使用建议

- **简单问答**：使用 `/api/chat` 或 `/api/chat/stream`
- **复杂任务**：使用 `/agent/chat`（支持工具调用）
- **多工具协作**：使用 `/agent/chat`

---

## ⚡ 性能优化

### 工具执行优化

- **异步执行**：支持异步工具执行
- **缓存机制**：工具结果可被缓存
- **并行调用**：支持多个工具并行调用

### 对话历史优化

- **摘要压缩**：长对话自动摘要
- **历史截断**：只保留最近 N 轮对话
- **语义压缩**：基于语义的历史压缩

---

## 🔒 安全特性

### 工具调用安全

- **参数验证**：工具参数严格校验
- **权限控制**：工具访问权限控制
- **执行限制**：工具执行时间限制

---

## 📊 监控与日志

### Agent 指标

| 指标 | 说明 |
|------|------|
| `agent_tool_calls_total` | 工具调用总数 |
| `agent_direct_answers_total` | 直接回答总数 |
| `agent_tool_call_duration_seconds` | 工具调用耗时 |
| `agent_errors_total` | Agent 错误总数 |

---

## 📚 参考文档

- [LangChain 工具文档](https://python.langchain.com/docs/modules/agents/tools/)
- [LangChain 核心模块](https://python.langchain.com/docs/langchain_core/)

---

## 📄 许可证

MIT License
