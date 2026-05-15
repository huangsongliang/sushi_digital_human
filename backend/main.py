"""FastAPI 主应用入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import chat_router
from backend.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="苏轼文化数字人问答系统 API"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat_router)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "苏轼文化数字人问答系统",
        "version": settings.app_version,
        "docs": "/docs",
        "redoc": "/redoc"
    }
