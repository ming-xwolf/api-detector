#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API检测器主入口模块
"""

import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.utils.logger import logger
from app.api.root import router as root_router
from app.api.detector import router as detector_router

# 初始化FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    description="检测代码库中的API类型和定义",
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
)

# 添加CORS中间件
# 处理CORS配置，将字符串"*"转换为列表["*"]
cors_origins = [settings.CORS_ORIGINS] if settings.CORS_ORIGINS != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(root_router)
app.include_router(detector_router)


@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    logger.info(f"{settings.APP_NAME} 服务启动")
    # 确保必要的目录存在
    settings.setup_directories()


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    logger.info(f"{settings.APP_NAME} 服务关闭")


if __name__ == "__main__":
    import uvicorn
    logger.info(f"以开发模式启动服务: {settings.HOST}:{settings.PORT}")
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        workers=settings.WORKERS
    ) 