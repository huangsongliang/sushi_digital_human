"""FastAPI 主应用入口"""
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from backend.api import chat_router
from backend.core.config import settings
from backend.utils.rate_limiter import rate_limit_middleware, concurrency_limit_middleware
from backend.utils.performance import generate_prometheus_metrics, get_prometheus_content_type
from backend.utils.error_tracking import setup_exception_handlers

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="苏轼文化数字人问答系统 API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
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

# 注册路由
app.include_router(chat_router)

# 设置全局异常处理器
setup_exception_handlers(app)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "苏轼文化数字人问答系统",
        "version": settings.app_version,
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "苏轼文化数字人问答系统",
        "version": settings.app_version
    }


@app.get("/metrics")
async def metrics():
    """Prometheus 指标端点"""
    metrics_data = generate_prometheus_metrics()
    content_type = get_prometheus_content_type()
    return Response(content=metrics_data, media_type=content_type)
