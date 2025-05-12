#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
清理工具模块 - 定期清理临时文件
"""

import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path

from app.core.config import settings
from app.services.file_service import cleanup_temp_files
from app.utils.logger import logger


async def schedule_cleanup(interval_hours: int = 24):
    """
    定期清理临时文件
    
    Args:
        interval_hours: 清理间隔（小时）
    """
    while True:
        try:
            logger.info(f"执行定期清理任务，保留最近{settings.TEMP_RETENTION_DAYS}天的文件")
            cleanup_temp_files(keep_days=settings.TEMP_RETENTION_DAYS)
            logger.info("清理任务完成")
        except Exception as e:
            logger.error(f"执行清理任务时出错: {str(e)}", exc_info=True)
            
        # 等待下一次执行
        await asyncio.sleep(interval_hours * 3600)  # 转换为秒


async def start_cleanup_task():
    """启动清理任务"""
    # 创建异步任务
    task = asyncio.create_task(schedule_cleanup())
    return task 