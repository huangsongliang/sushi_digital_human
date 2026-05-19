"""FastAPI 主应用入口"""

import signal
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Response, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from backend.api import chat_router, ab_test_router, dify_router, documents_router, alerts_router, auth_router
from backend.core.config import settings
from backend.database.session import async_initialize_database
from backend.utils.rate_limiter import (
    rate_limit_middleware,
    concurrency_limit_middleware,
)
from backend.utils.performance import (
    generate_prometheus_metrics,
    get_prometheus_content_type,
)
from backend.utils.error_tracking import setup_exception_handlers
from backend.utils.logger import get_logger
from backend.utils.health import perform_health_check, shutdown_manager, health_checker
from backend.utils.alerting import start_alerting, stop_alerting

logger = get_logger(__name__)


def setup_shutdown_signal_handlers(app: FastAPI):
    """设置关闭信号处理器"""

    def handle_shutdown(signum, frame):
        logger.info(f"收到关闭信号 {signum}")
        shutdown_manager.initiate_shutdown()

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info("启动应用...")

    # 设置关闭信号处理器
    setup_shutdown_signal_handlers(app)

    # 初始化数据库
    logger.info("初始化数据库...")
    await async_initialize_database()
    logger.info("数据库初始化完成")

    # 初始化默认角色和权限
    logger.info("初始化默认角色和权限...")
    from backend.core.auth_manager import initialize_default_roles_and_permissions
    await initialize_default_roles_and_permissions()
    logger.info("角色和权限初始化完成")

    # 启动告警系统
    logger.info("启动告警系统...")
    await start_alerting()
    logger.info("告警系统启动完成")

    yield

    # 关闭时清理
    logger.info("关闭应用...")

    # 停止告警系统
    logger.info("停止告警系统...")
    await stop_alerting()
    logger.info("告警系统已停止")

    # 等待所有请求完成
    await shutdown_manager.wait_for_requests_to_complete()

    # 关闭 LLM 线程池
    try:
        from backend.generator import get_async_llm

        llm = get_async_llm()
        llm.close()
    except Exception as e:
        logger.warning(f"关闭 LLM 线程池失败: {str(e)}")

    # 关闭缓存嵌入模型线程池
    try:
        from backend.generator import get_cached_embeddings

        embeddings = get_cached_embeddings()
        embeddings.close()
    except Exception as e:
        logger.warning(f"关闭嵌入模型线程池失败: {str(e)}")

    logger.info("应用已优雅关闭")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="企业级智能文档问答平台 API - 基于 RAG 的企业级知识库问答系统",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# 请求体大小限制
app.state.max_request_size = 10 * 1024 * 1024  # 10MB

# GZip 压缩中间件（提升传输性能）
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 信任主机中间件（安全防护）
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])


# 限流中间件（性能保护）
@app.middleware("http")
async def add_rate_limit_middleware(request, call_next):
    return await rate_limit_middleware(request, call_next)


# 并发限制中间件（控制并发数）
@app.middleware("http")
async def add_concurrency_limit_middleware(request, call_next):
    return await concurrency_limit_middleware(request, call_next)


# 请求计数中间件（用于优雅关闭）
@app.middleware("http")
async def add_request_count_middleware(request, call_next):
    shutdown_manager.increment_request_count()
    try:
        return await call_next(request)
    finally:
        shutdown_manager.decrement_request_count()


# 注册路由
app.include_router(chat_router)
app.include_router(ab_test_router)
app.include_router(dify_router)
app.include_router(documents_router)
app.include_router(auth_router)
app.include_router(alerts_router)

# 设置全局异常处理器
setup_exception_handlers(app)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "企业级智能文档问答平台",
        "version": settings.app_version,
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health")
async def health_check():
    """健康检查 - 返回详细的服务健康状态"""
    report = await perform_health_check()

    # 根据健康状态设置 HTTP 状态码
    status_code = 200
    if report["status"] == "degraded":
        status_code = 200  # 降级状态仍返回 200
    elif report["status"] == "unhealthy":
        status_code = 503  # 不健康状态返回 503

    return JSONResponse(content=report, status_code=status_code)


@app.get("/health/liveness")
async def liveness_check():
    """存活检查 - 检查服务是否正在运行"""
    return {"status": "alive", "timestamp": time.time()}


@app.get("/health/readiness")
async def readiness_check():
    """就绪检查 - 检查服务是否准备好处理请求"""
    report = await perform_health_check()

    if report["status"] == "unhealthy":
        raise HTTPException(status_code=503, detail="服务未就绪")

    return {"status": "ready", "timestamp": time.time()}


@app.get("/metrics")
async def metrics():
    """Prometheus 指标端点"""
    metrics_data = generate_prometheus_metrics()
    content_type = get_prometheus_content_type()
    return Response(content=metrics_data, media_type=content_type)
