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
- 2026-05-23 (late): 推送全部企业级功能模块代码到 GitHub (64 files, 19371+ lines)。修复 pre-commit 钩子错误（permission_rules dict→list、import asyncio、flake8 E226/E712）。docker compose 生产部署测试通过 — 4 个核心容器全部 healthy (MySQL/Redis/API/Nginx)，API 健康检查返回正常，Nginx 前端页面 200。nginx 端口从 80/443 改为 8080/8443（避开本机占用）。
- 2026-05-23: CI/CD 流水线修复（3/3 问题全部解决）— flake8 配置路径修正、docker-compose 测试改用 apt 装 docker-compose-v2、K8s 连通性检查改进（真正测试 kubectl cluster-info 而非静默忽略）。最终确定生产部署方案 A：docker compose 替代 K8s。
- 2026-05-22: 全量改进登录注册功能 — 后端加密码强度校验(8位+大小写+数字+特殊字符)、Redis 登录限流(5次/15分钟)、GitHub 回调 URL 配置化(FRONTEND_URL)。前端创建集中式 HTTP 客户端(request.ts)支持 Token 自动刷新+401重试、重写 AuthPage 添加字段级校验+密码强度条+密码显示切换+注册成功提示+独立SMS倒计时、路由监听 auth:logout 事件自动跳转。
