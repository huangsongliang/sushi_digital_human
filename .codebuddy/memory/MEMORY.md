# Memory

## 项目技术栈与约定
- 后端: FastAPI + Python 3.11+ + LangChain 0.3+ + ChromaDB + Redis + MySQL
- 前端: Vue 3 + TypeScript + Element Plus + Vite + Pinia
- 包管理: 后端 uv，前端 npm
- 启动命令: `uv run uvicorn backend.main:app --reload --port 8000` + `cd frontend && npx vite --port 5173`
- Vite proxy 配置将 `/api` 代理到 `http://localhost:8000`

## 开发约定
- Python: strict type annotations, snake_case, docstrings with Args/Returns/Raises
- Vue: PascalCase 组件, <script setup lang="ts">, scoped styles, 禁止直接解构 Pinia store
- 敏感信息放在 .env 中，通过 pydantic-settings 管理

## 项目命名
- **项目名**：企业级智能文档问答平台（Enterprise Document Q&A Platform）
- **代号** `sushi` 保留：Docker 镜像名、Prometheus 指标、Helm release、数据库名
- **注意**：2026-05-24 已清理全部中文"苏轼"引用，sushi 仅作为项目代号保留

## 评估系统
- **框架**：LangSmith（LangChain 官方平台）
- **脚本**：`tests/evaluation/langsmith_eval.py`
- **数据集**：`tests/evaluation/dataset/sample_eval.json`（10 条企业级评估数据）
- **评估指标**：Hit Rate@K、MRR、语义相似度、Faithfulness、Answer Relevance
- **运行**：`uv run python tests/evaluation/langsmith_eval.py`（本地模式）
- **在线模式**：需配置 `LANGCHAIN_API_KEY` 环境变量

## 生产部署
- **方案 A（当前采用）**：`docker compose -f docker-compose.prod.yml up -d`，8 服务（MySQL/Redis/API/Nginx/Prometheus/Grafana/Loki/Promtail）
- 前端需先构建：`cd frontend && npm run build`，产物在 `frontend/dist/`
- CI 中 `helm-deploy` job 自动跳过 K8s 部署（KUBE_CONFIG 无可用集群时静默跳过）
- 暂不启用 K8s 集群（需要公网 IP 的 ACK 集群，对个人项目过度工程）
- CI 覆盖阈值设 30%（pyproject.toml `fail_under=30`），跨平台差异大（CI~44%, 本地~36%）

## CI/CD Pipeline
- workflow: `.github/workflows/ci-cd.yml` (6 jobs)
- 后端测试跳过 torch/transformers 等重依赖（仅装最小集合）
- 前端构建含 vue-tsc 类型检查（本地验证通过）
- Docker 构建仅 push main 分支时触发

## K8s 部署结构（备用）
- Chart: `helm/sushi-digital-human/`，CI/CD: `.github/workflows/ci-cd.yml`
- GitHub Secrets 需要: `DASHSCOPE_API_KEY`, `SECRET_KEY`, `KUBE_CONFIG`（需配置公网可达集群）

## 生产环境端口
- MySQL: 3307, Redis: 6379, API: 8082, Nginx: 8080/8443
- Prometheus: 9090, Grafana: 3000, Loki: 3100

## 完成的工作
- 2026-05-24: 清理全部"苏轼"中文引用（18 个文件）+ 搭建 LangSmith 评估系统（tests/evaluation/）
- 2026-05-23 (late): 推送全部企业级功能模块代码到 GitHub (64 files, 19371+ lines)。修复 pre-commit 钩子错误（permission_rules dict→list、import asyncio、flake8 E226/E712）。docker compose 生产部署测试通过 — 4 个核心容器全部 healthy (MySQL/Redis/API/Nginx)，API 健康检查返回正常，Nginx 前端页面 200。nginx 端口从 80/443 改为 8080/8443（避开本机占用）。
- 2026-05-23: CI/CD 流水线修复（3/3 问题全部解决）— flake8 配置路径修正、docker-compose 测试改用 apt 装 docker-compose-v2、K8s 连通性检查改进（真正测试 kubectl cluster-info 而非静默忽略）。最终确定生产部署方案 A：docker compose 替代 K8s。
- 2026-05-22: 全量改进登录注册功能 — 后端加密码强度校验(8位+大小写+数字+特殊字符)、Redis 登录限流(5次/15分钟)、GitHub 回调 URL 配置化(FRONTEND_URL)。前端创建集中式 HTTP 客户端(request.ts)支持 Token 自动刷新+401重试、重写 AuthPage 添加字段级校验+密码强度条+密码显示切换+注册成功提示+独立SMS倒计时、路由监听 auth:logout 事件自动跳转。
## 法律诉讼智能体 - 方案决策 (2026-05-25)

### 总体策略
- **定位**: 诉讼策略分析工具（差异化于秘塔AI的「法律检索」定位），面向中小律所
- **实施路径**: 三阶段递进 —— MVP 验证（2-3周）→ 产品化（4-6周）→ 商业化（8-12周）
- **项目分离**: 法律 Agent 将新建独立项目实施，sushi_digital_human 作为开源作品集保留

### MVP 阶段范围
- ✅ PDF 卷宗上传 + OCR 识别（PyMuPDF + PaddleOCR）
- ✅ 法律 NER 抽取（通用 NER + LLM few-shot，不引入专用模型）
- ✅ 简单知识图谱（仅「人物-证据」关系）
- ✅ 基于向量检索的问答（复用现有 RAG）
- ✅ 固定模板报告生成（LLM 填槽）
- ❌ 不包含：判例检索、复杂图谱、多 Agent 协作、协作功能

### 判例库策略
- MVP 阶段用通用网络搜索代替判例检索
- 第二阶段先手动录入 100 个典型案例验证效果
- 判例分三级权威：指导性案例（最高法，必须参考）→ 公报案例（强参考）→ 普通判例（弱参考）

### 关键技术决策
- OCR 引擎：EasyOCR（现有）→ 后期换 PaddleOCR（中文法律文档更好）
- NER 方案：通用 NER + LLM few-shot（MVP 阶段），不引入法律专用 NER 模型
- 图谱存储：现有 Mock 模式（开发），生产环境需部署 Neo4j
- 报告生成：固定法律模板 + LLM 填槽，非自由生成
- 架构：单 Agent（MVP）→ 多 Agent 协作（产品化阶段）

### 差异化竞争点
- 「证据链可视化」而非单纯知识图谱
- 「诉讼策略建议」而非简单法条检索
- 支持反诉 + 多被告复杂场景

### 规则文件
- `.codebuddy/rules/legal-agent-conventions.md`：法律 Agent 代码约定（alwaysApply: true），含实体类型、关系命名、安全合规、报告格式规范

## 开源隐私清理 (2026-05-25)

### 已清理的敏感信息
- DashScope API Key `sk-6c868...`：已吊销 + 替换为 `your-api-key-here`（3 处：PROJECT_SUMMARY.md x2, 2026-05-15_PROGRESS.md x1）
- MySQL 密码 `7531188`：docker-compose.prod.yml 3 处 fallback 值改为 `changeme`
- GitHub Client Secret：全项目搜索确认无残留
- 根目录垃圾文件：`localStorage.setItem(...)`, `$null`, `{` 已删除
- `.env` 从未被 Git 提交，`.env.example` 全占位符

### 待处理风险
- API Key 仍存于 Git 历史中（`docs/PROJECT_SUMMARY.md`），开源前建议用 `git filter-branch` 或 BFG 清理，或直接以当前状态创建新仓库
