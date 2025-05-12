#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
日志工具模块 - 配置应用日志
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import settings


def setup_logger(name: str = "api_detector") -> logging.Logger:
    """
    设置应用日志记录器
    
    Args:
        name: 记录器名称
        
    Returns:
        配置好的记录器实例
    """
    # 创建记录器
    logger = logging.getLogger(name)
    
    # 如果已经配置过，直接返回
    if logger.handlers:
        return logger
        
    # 设置日志级别
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # 创建文件处理器
    log_file = Path(settings.LOG_FILE)
    # 确保日志目录存在
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    
    # 创建格式化器
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format)
    
    # 添加格式化器到处理器
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # 添加处理器到记录器
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    # 记录环境信息
    logger.info(f"应用启动 - 环境: {settings.APP_ENV}, 调试模式: {settings.DEBUG}")
    logger.debug(f"日志级别设置为: {settings.LOG_LEVEL}")
    
    return logger


# 创建默认记录器实例
logger = setup_logger() 