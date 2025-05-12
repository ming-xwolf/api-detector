#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件处理服务 - 处理上传文件和临时存储
"""

import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile

from fastapi import UploadFile

from app.core.config import settings
from app.utils.logger import logger


async def save_upload_file(file: UploadFile) -> Path:
    """
    保存上传的文件到临时目录
    
    Args:
        file: 上传的文件
        
    Returns:
        保存文件的路径
    """
    # 生成唯一文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    filename = f"{timestamp}_{unique_id}_{file.filename}"
    
    # 构建保存路径
    save_path = Path(settings.UPLOAD_DIR) / filename
    
    # 确保目录存在
    save_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 保存文件
    with open(save_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    logger.info(f"文件已保存: {save_path}")
    return save_path


async def extract_zip(zip_path: Path) -> Path:
    """
    解压ZIP文件到临时目录
    
    Args:
        zip_path: ZIP文件路径
        
    Returns:
        解压后的目录路径
    """
    # 创建解压目录
    extract_dir = Path(settings.TEMP_DIR) / zip_path.stem
    
    # 如果目录已存在，先删除
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    
    # 创建目录
    extract_dir.mkdir(parents=True, exist_ok=True)
    
    # 解压文件
    with ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    
    logger.info(f"ZIP文件已解压到: {extract_dir}")
    return extract_dir


def cleanup_temp_files(file_path: Path = None, keep_days: int = 1):
    """
    清理临时文件
    
    Args:
        file_path: 指定要删除的文件路径，如果为None则清理所有过期文件
        keep_days: 保留文件的天数
    """
    if file_path and file_path.exists():
        if file_path.is_file():
            file_path.unlink()
        elif file_path.is_dir():
            shutil.rmtree(file_path)
        logger.info(f"已删除: {file_path}")
        return
    
    # 清理上传目录中的过期文件
    now = datetime.now()
    for dir_path in [settings.UPLOAD_DIR, settings.TEMP_DIR]:
        dir_path = Path(dir_path)
        if not dir_path.exists():
            continue
            
        for item in dir_path.iterdir():
            if not item.is_file() and not item.is_dir():
                continue
                
            # 获取文件修改时间
            mtime = datetime.fromtimestamp(item.stat().st_mtime)
            # 计算文件存在的天数
            days_old = (now - mtime).days
            
            # 如果文件超过保留天数，则删除
            if days_old > keep_days:
                if item.is_file():
                    item.unlink()
                else:
                    shutil.rmtree(item)
                logger.info(f"已删除过期项: {item} (已存在 {days_old} 天)") 