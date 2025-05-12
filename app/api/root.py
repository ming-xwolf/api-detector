#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
根路由API
"""

from fastapi import APIRouter

from app.core.config import settings
from app.utils.logger import logger

router = APIRouter(tags=["root"])


@router.get("/")
def read_root():
    """首页路由"""
    logger.debug("访问首页")
    return {
        "message": f"欢迎使用{settings.APP_NAME}",
        "status": "运行中",
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV
    }


@router.get("/health")
def health_check():
    """健康检查端点"""
    logger.debug("健康检查")
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION
    } 