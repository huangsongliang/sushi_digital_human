# Dockerfile - 企业级智能文档问答系统 API 服务
# 支持多阶段构建、健康检查、日志管理、安全配置

# ==================== 第一阶段：构建 ====================
FROM python:3.11-slim AS builder

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=1.8.3

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# 创建虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 升级 pip
RUN pip install --upgrade pip setuptools wheel

# 配置清华镜像源（加速下载）
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 复制依赖文件
COPY pyproject.toml uv.lock ./

# 使用 uv 安装依赖
RUN pip install uv && uv pip install --system -e .

# ==================== 第二阶段：运行（开发）====================
FROM python:3.11-slim AS development

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    ENV=development \
    LOG_LEVEL=debug

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 设置工作目录
WORKDIR /app

# 复制应用代码
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY config/ ./config/
COPY pyproject.toml .

# 创建数据和日志目录
RUN mkdir -p /app/data /app/logs /app/migrations

# 创建非 root 用户
RUN groupadd -r appuser && useradd -r -g appuser appuser && \
    chown -R appuser:appuser /app

# 切换用户
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/liveness || exit 1

# 开发环境启动命令（热重载）
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "debug"]

# ==================== 第三阶段：生产环境 ====================
FROM python:3.11-slim AS production

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    ENV=production \
    LOG_LEVEL=info \
    PROMETHEUS_ENABLED=true

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 设置工作目录
WORKDIR /app

# 复制应用代码（仅后端代码）
COPY backend/ ./backend/
COPY config/ ./config/
COPY migrations/ ./migrations/
COPY pyproject.toml alembic.ini ./

# 创建数据和日志目录
RUN mkdir -p /app/data /app/logs /app/migrations

# 创建非 root 用户
RUN groupadd -r appuser && useradd -r -g appuser appuser && \
    chown -R appuser:appuser /app

# 切换用户
USER appuser

# 暴露端口
EXPOSE 8000 9090

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health/readiness || exit 1

# 生产环境启动命令（多 worker + Gunicorn）
CMD ["gunicorn", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "--log-level", "info", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "backend.main:app"]

# ==================== 第四阶段：监控侧车容器 ====================
FROM python:3.11-slim AS monitoring

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --upgrade pip && \
    pip install prometheus-client

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY config/prometheus/ ./config/prometheus/

EXPOSE 9090

CMD ["python", "-c", "from prometheus_client import start_http_server; start_http_server(9090); import time; while True: time.sleep(1)"]
