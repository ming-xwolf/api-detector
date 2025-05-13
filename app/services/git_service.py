#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Git服务 - 处理Git仓库
"""

from pathlib import Path
from typing import Optional, Dict, Any

from app.services.git_providers import GitProviderFactory
from app.utils.logger import logger


async def get_repo_default_branch(repo_url: str) -> str:
    """
    获取Git仓库的默认分支
    
    Args:
        repo_url: 仓库URL
        
    Returns:
        默认分支名称
    """
    try:
        # 创建适当的Git提供商
        provider = await GitProviderFactory.create_provider(repo_url)
        
        # 获取默认分支
        return await provider.get_default_branch()
    except Exception as e:
        logger.error(f"获取仓库默认分支时出错: {str(e)}")
        # 如果无法获取默认分支，返回常见的默认分支名称
        return "main"


async def clone_repository(repo_url: str, branch: Optional[str] = None) -> Path:
    """
    克隆Git仓库到临时目录
    
    Args:
        repo_url: Git仓库URL
        branch: 分支名，如果为None则使用默认分支
        
    Returns:
        克隆后的目录路径
    """
    # 创建适当的Git提供商
    provider = await GitProviderFactory.create_provider(repo_url)
    
    # 克隆仓库
    return await provider.clone_repository(branch)


async def download_repository_zip(repo_url: str, branch: Optional[str] = None) -> Path:
    """
    下载Git仓库的ZIP文件
    
    Args:
        repo_url: Git仓库URL
        branch: 分支名，如果为None则使用默认分支
        
    Returns:
        下载的ZIP文件路径
    """
    # 创建适当的Git提供商
    provider = await GitProviderFactory.create_provider(repo_url)
    
    # 下载仓库ZIP文件
    return await provider.download_zip(branch)


async def get_repo_info(repo_url: str) -> Dict[str, Any]:
    """
    获取Git仓库基本信息
    
    Args:
        repo_url: Git仓库URL
        
    Returns:
        包含仓库信息的字典
    """
    try:
        # 创建适当的Git提供商
        provider = await GitProviderFactory.create_provider(repo_url)
        
        # 获取仓库信息
        return await provider.get_repo_info()
    except Exception as e:
        logger.error(f"获取仓库信息时出错: {str(e)}")
        return {
            "url": repo_url,
            "type": "unknown"
        } 