#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
下载工具类 - 提供通用的下载功能
"""

import httpx
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from app.core.config import settings

# 获取日志记录器
logger = logging.getLogger(__name__)

class DownloadUtils:
    """下载工具类，提供通用的下载功能"""
    
    @staticmethod
    async def download_zip_from_url(
        zip_url: str, 
        output_path: Path,
        headers: Optional[Dict[str, str]] = None
    ) -> Path:
        """
        从URL下载ZIP文件
        
        Args:
            zip_url: ZIP文件的URL
            output_path: 保存ZIP文件的路径
            headers: 可选的HTTP请求头
            
        Returns:
            下载的ZIP文件路径
            
        Raises:
            ValueError: 当下载失败时抛出
        """
        # 确保目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 如果文件已存在，先删除
        if output_path.exists():
            output_path.unlink()
            
        logger.info(f"正在下载ZIP文件: {zip_url}")
        
        try:
            # 设置默认请求头
            if headers is None:
                headers = {}
                
            # 下载ZIP文件
            timeout = httpx.Timeout(60.0)
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                with client.stream("GET", zip_url, headers=headers) as response:
                    response.raise_for_status()
                    
                    # 写入文件
                    with open(output_path, "wb") as f:
                        for chunk in response.iter_bytes(chunk_size=8192):
                            f.write(chunk)
                            
            logger.info(f"ZIP文件下载成功: {output_path}")
            return output_path
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"下载的文件不存在: {zip_url}")
                raise ValueError(f"下载的文件不存在: {zip_url}")
            else:
                logger.error(f"下载ZIP文件失败: {str(e)}")
                raise ValueError(f"下载ZIP文件失败: {str(e)}")
        except Exception as e:
            logger.error(f"下载ZIP文件时出错: {str(e)}")
            raise ValueError(f"下载ZIP文件时出错: {str(e)}") 