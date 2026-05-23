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

## K8s 部署结构（Docker Desktop）
- Namespace: `sushi`，Chart: `helm/sushi-digital-human/`
- 组件: API (3副本) + Nginx (2副本) + Redis (1副本) + MySQL (1副本)
- 前端: 构建到 `frontend/dist/`，打入同一 Docker 镜像，nginx init container 复制到 emptyDir volume
- MySQL: 手动部署（不用 bitnami chart，国内网络不通），PVC 用 hostpath StorageClass，允许空密码（开发环境）
- 访问: `kubectl port-forward svc/sushi-digital-human-sushi-digital-human-nginx -n sushi 8089:80`
- CI/CD: `.github/workflows/ci-cd.yml`，6 job 覆盖 lint/test/build/push/deploy/compose-test
- GitHub Secrets 需要: `DASHSCOPE_API_KEY`, `SECRET_KEY`, `KUBE_CONFIG`

## 完成的工作
- 2026-05-23: K8s 集群完整部署（API+Nginx+Redis+MySQL），前端 dist 分发修复，MySQL 手动部署替代 bitnami chart，CI/CD 流水线分析完成
- 2026-05-22: 全量改进登录注册功能 — 后端加密码强度校验(8位+大小写+数字+特殊字符)、Redis 登录限流(5次/15分钟)、GitHub 回调 URL 配置化(FRONTEND_URL)。前端创建集中式 HTTP 客户端(request.ts)支持 Token 自动刷新+401重试、重写 AuthPage 添加字段级校验+密码强度条+密码显示切换+注册成功提示+独立SMS倒计时、路由监听 auth:logout 事件自动跳转。
