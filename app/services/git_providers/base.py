#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Git提供商基类 - 定义Git仓库操作的接口
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any, List

from app.utils.download_utils import DownloadUtils


class GitProvider(ABC):
    """Git提供商抽象基类"""
    
    @classmethod
    @abstractmethod
    async def can_handle(cls, repo_url: str) -> bool:
        """
        检查该提供商是否可以处理指定的仓库URL
        
        Args:
            repo_url: 仓库URL
            
        Returns:
            如果可以处理则返回True，否则返回False
        """
        pass
    
    @abstractmethod
    async def get_default_branch(self) -> str:
        """
        获取仓库的默认分支
        
        Returns:
            默认分支名称
        """
        pass
    
    def get_default_branch_download(self) -> List[str]:
        """
        获取常见的默认分支列表
        
        Returns:
            常见默认分支名称列表
        """
        return ["main", "master", "develop", "trunk", "default"]
    
    @abstractmethod
    async def clone_repository(self, branch: Optional[str] = None) -> Path:
        """
        克隆仓库到临时目录
        
        Args:
            branch: 分支名，如果为None则使用默认分支
            
        Returns:
            克隆后的目录路径
        """
        pass
    
    @abstractmethod
    async def download_zip(self, branch: Optional[str] = None) -> Path:
        """
        下载仓库的ZIP文件
        
        Args:
            branch: 分支名，如果为None则使用默认分支
            
        Returns:
            下载的ZIP文件路径
        """
        pass
    
    @abstractmethod
    async def download_zip_from_branch(self, branch: str) -> Path:
        """
        根据指定分支构造ZIP URL并下载仓库ZIP文件
        
        Args:
            branch: 分支名称
            
        Returns:
            下载的ZIP文件路径
        """
        pass
    
    async def download_zip_from_url(self, zip_url: str, output_path: Path) -> Path:
        """
        从URL下载仓库的ZIP文件
        
        Args:
            zip_url: ZIP文件的URL
            output_path: 保存ZIP文件的路径
            
        Returns:
            下载的ZIP文件路径
        """
        return await DownloadUtils.download_zip_from_url(zip_url, output_path)
    
    @abstractmethod
    async def get_repo_info(self) -> Dict[str, Any]:
        """
        获取仓库的基本信息
        
        Returns:
            包含仓库信息的字典
        """
        pass
    
    @property
    @abstractmethod
    def repo_url(self) -> str:
        """获取仓库URL"""
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """获取提供商名称"""
        pass 