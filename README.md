# 苏轼文化数字人问答系统

> 基于 RAG（Retrieval-Augmented Generation）的文化知识库问答系统

## 项目简介

本项目是一个面向苏轼文化研究的智能问答系统，通过检索增强生成技术，为用户提供准确、权威的苏轼相关知识问答服务。

## 技术栈

- **前端**: Vue 3 + TypeScript + Element Plus
- **后端**: FastAPI + Python 3.11
- **AI 框架**: LangChain 0.3
- **大语言模型**: 通义千问 (DashScope)
- **向量数据库**: ChromaDB / Milvus
- **缓存**: Redis
- **部署**: Docker + Docker Compose

## 快速开始

### 环境要求

- Python >= 3.11
- uv (包管理工具)
- Redis 7.0+ (可选)
- MySQL 8.0+ (可选)

### 安装依赖

```bash
# 使用 uv 安装依赖
uv sync

# 或者使用 pip
pip install -e .
```

### 配置环境变量

复制 `.env.example` 为 `.env` 并配置相关参数：

```bash
cp .env.example .env
```

### 启动服务

```bash
# 开发模式
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### 访问服务

- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

## 项目结构

```
sushi_digital_human/
├── backend/              # 后端应用
│   ├── api/             # API 路由
│   ├── chain/           # LangChain 链定义
│   ├── core/            # 核心配置
│   ├── generator/       # LLM 生成器
│   ├── memory/          # 对话记忆
│   ├── models/          # 数据模型
│   ├── retrieval/       # 检索模块
│   ├── utils/           # 工具函数
│   └── main.py          # FastAPI 入口
├── docs/                # 项目文档
├── data/                # 数据目录
├── tests/               # 测试用例
└── scripts/             # 脚本工具
```

## API 接口

### 聊天接口

```bash
POST /api/chat
Content-Type: application/json

{
  "message": "苏轼的代表作有哪些？",
  "session_id": "user_123",
  "stream": true
}
```

### 健康检查

```bash
GET /api/health
```

## 开发路线图

- [x] 阶段 0: 工程化重构
- [ ] 阶段 1: LangChain 基础实现
- [ ] 阶段 2: 混合检索
- [ ] 阶段 3: 重排序优化
- [ ] 阶段 4: API 开发
- [ ] 阶段 5: 前端开发
- [ ] 阶段 6: 部署运维
- [ ] 阶段 7: Agent 扩展

## 贡献指南

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License
