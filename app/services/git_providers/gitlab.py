#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GitLab提供商 - 处理GitLab仓库
"""

import os
import shutil
import urllib.parse
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional, Dict, Any

import git
import httpx

from app.core.config import settings
from app.services.git_providers.base import GitProvider
from app.utils.logger import logger


class GitLabProvider(GitProvider):
    """GitLab提供商实现"""
    
    def __init__(self, repo_url: str):
        """
        初始化GitLab提供商
        
        Args:
            repo_url: GitLab仓库URL
        """
        self._repo_url = repo_url
        self._parsed_url = urlparse(repo_url)
        self._path_parts = self._parsed_url.path.strip("/").split("/")
        
        # GitLab可能有更深的路径结构，如组/子组/项目
        self._repo_name = self._path_parts[-1].replace('.git', '')
        
        # 项目路径，包括所有组和子组
        self._project_path = '/'.join(self._path_parts)
        
        # URL编码的项目路径，用于API调用
        self._encoded_project_path = urllib.parse.quote_plus(self._project_path)
    
    @classmethod
    async def can_handle(cls, repo_url: str) -> bool:
        """
        检查是否可以处理指定的仓库URL
        
        Args:
            repo_url: 仓库URL
            
        Returns:
            如果是GitLab URL则返回True，否则返回False
        """
        # 从设置中获取域名
        gitlab_domain = urlparse(settings.GITLAB_BASE_URL).netloc
        return gitlab_domain.lower() in repo_url.lower()
    
    async def get_default_branch(self) -> str:
        """
        获取仓库的默认分支
        
        Returns:
            默认分支名称
        """
        # 构建API URL
        api_url = f"{settings.GITLAB_API_URL}/projects/{self._encoded_project_path}"
        logger.debug(f"获取GitLab仓库默认分支: {api_url}")
        
        try:
            # 使用同步客户端请求GitLab API
            headers = {"Accept": "application/json"}
            
            # 如果设置了Git令牌，添加到请求头
            if settings.GIT_TOKEN:
                headers["PRIVATE-TOKEN"] = settings.GIT_TOKEN
                
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                response = client.get(api_url, headers=headers)
                response.raise_for_status()
                
                repo_info = response.json()
                default_branch = repo_info.get("default_branch", "main")
                logger.info(f"GitLab仓库默认分支: {default_branch}")
                return default_branch
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"GitLab仓库不存在: {self._project_path}")
                raise ValueError(f"GitLab仓库不存在: {self._project_path}")
            else:
                logger.error(f"获取GitLab仓库信息失败: {str(e)}")
                raise ValueError(f"获取GitLab仓库信息失败: {str(e)}")
        except Exception as e:
            logger.error(f"获取GitLab仓库默认分支时出错: {str(e)}")
            # 尝试使用通用方法
            return await super().get_default_branch() if hasattr(super(), 'get_default_branch') else "main"
    
    async def download_zip(self, branch: Optional[str] = None) -> Path:
        """
        下载仓库的ZIP文件
        
        Args:
            branch: 分支名，如果为None则使用默认分支列表依次尝试
            
        Returns:
            下载的ZIP文件路径
        """
        # 如果指定了分支，直接下载该分支
        if branch is not None:
            return await self.download_zip_from_branch(branch)
            
        # 如果没有指定分支，获取默认分支列表，依次尝试下载
        default_branches = self.get_default_branch_download()
        last_error = None
        
        for current_branch in default_branches:
            try:
                logger.info(f"尝试下载分支 {current_branch} 的ZIP文件")
                return await self.download_zip_from_branch(current_branch)
            except ValueError as e:
                logger.warning(f"下载分支 {current_branch} 失败: {str(e)}")
                last_error = e
                continue
                
        # 如果所有分支都失败，抛出最后一个错误
        raise ValueError(f"所有默认分支下载失败，最后错误: {str(last_error)}")
    
    async def download_zip_from_branch(self, branch: str) -> Path:
        """
        根据指定分支构造ZIP URL并下载仓库ZIP文件
        
        Args:
            branch: 分支名称
            
        Returns:
            下载的ZIP文件路径
        """
        # 构建ZIP下载URL
        zip_url = f"{settings.GITLAB_API_URL}/projects/{self._encoded_project_path}/repository/archive.zip?sha={branch}"
        
        # 创建保存路径
        zip_file_path = Path(settings.TEMP_DIR) / f"gitlab_{self._project_path.replace('/', '_')}_{branch}.zip"
        
        logger.info(f"正在下载GitLab仓库ZIP: {self._repo_url} (分支: {branch})")
        
        try:
            # 使用基类的辅助方法下载ZIP文件
            return await self.download_zip_from_url(zip_url, zip_file_path)
        except ValueError as e:
            # 重新抛出异常，添加更多上下文信息
            if "下载的文件不存在" in str(e):
                raise ValueError(f"GitLab仓库或分支不存在: {self._project_path}/{branch}")
            else:
                raise ValueError(f"下载GitLab仓库ZIP失败: {str(e)}")
    
    async def clone_repository(self, branch: Optional[str] = None) -> Path:
        """
        克隆仓库到临时目录
        
        Args:
            branch: 分支名，如果为None则使用默认分支
            
        Returns:
            克隆后的目录路径
        """
        # 如果没有指定分支，获取默认分支
        if branch is None:
            try:
                branch = await self.get_default_branch()
            except Exception:
                branch = "main"
        
        # 创建临时目录
        clone_dir = Path(settings.TEMP_DIR) / f"gitlab_{self._repo_name}_{branch}"
        
        # 如果目录已存在，先删除
        if clone_dir.exists():
            shutil.rmtree(clone_dir)
        
        # 创建目录
        clone_dir.mkdir(parents=True, exist_ok=True)
        
        # 构建克隆命令
        logger.info(f"正在克隆GitLab仓库: {self._repo_url} (分支: {branch})")
        
        # 处理认证信息
        auth_url = self._repo_url
        
        # 检查是否有提供令牌
        if settings.GIT_TOKEN:
            auth_url = self._repo_url.replace('https://', f'https://oauth2:{settings.GIT_TOKEN}@')
            logger.debug("使用GitLab令牌进行认证")
            
        try:
            # 克隆仓库
            git.Repo.clone_from(auth_url, clone_dir, branch=branch, depth=1)
            logger.info(f"GitLab仓库克隆成功: {clone_dir}")
            return clone_dir
        except git.exc.GitCommandError as e:
            logger.error(f"克隆GitLab仓库失败: {str(e)}")
            if "not found" in str(e).lower():
                # 可能是私有仓库或不存在
                raise ValueError(f"GitLab仓库未找到或需要访问权限。如果是私有仓库，请提供有效的GitLab令牌。")
            elif "could not read Username" in str(e):
                raise ValueError(f"需要访问权限克隆此GitLab仓库。请提供有效的GitLab令牌。")
            raise ValueError(f"克隆GitLab仓库失败: {str(e)}")
    
    async def get_repo_info(self) -> Dict[str, Any]:
        """
        获取仓库的基本信息
        
        Returns:
            包含仓库信息的字典
        """
        try:
            # 构建API URL
            api_url = f"{settings.GITLAB_API_URL}/projects/{self._encoded_project_path}"
            logger.debug(f"GitLab API URL: {api_url}")
            
            # 创建一个新的httpx客户端
            limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)
            timeout = httpx.Timeout(10.0, connect=5.0)
            
            async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
                # 设置最小化的请求头
                headers = {"Accept": "application/json"}
                
                # 如果设置了Git令牌，添加到请求头
                if settings.GIT_TOKEN:
                    headers["PRIVATE-TOKEN"] = settings.GIT_TOKEN
                    
                # 发送请求
                response = await client.get(api_url, headers=headers)
                response.raise_for_status()
                
                # 解析响应
                repo_info = response.json()
                
                # 提取感兴趣的信息
                result = {
                    "url": self._repo_url,
                    "type": "gitlab",
                    "repo_name": self._repo_name,
                    "project_path": self._project_path,
                    "name": repo_info.get("name", ""),
                    "path_with_namespace": repo_info.get("path_with_namespace", ""),
                    "description": repo_info.get("description", ""),
                    "default_branch": repo_info.get("default_branch", "main"),
                    "visibility": repo_info.get("visibility", ""),
                    "star_count": repo_info.get("star_count", 0),
                    "forks_count": repo_info.get("forks_count", 0),
                    "open_issues_count": repo_info.get("open_issues_count", 0),
                    "created_at": repo_info.get("created_at", ""),
                    "last_activity_at": repo_info.get("last_activity_at", "")
                }
                
                # 如果有命名空间信息，添加到结果中
                if "namespace" in repo_info:
                    result["namespace"] = {
                        "name": repo_info["namespace"].get("name", ""),
                        "path": repo_info["namespace"].get("path", ""),
                        "kind": repo_info["namespace"].get("kind", "")
                    }
                
                return result
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"GitLab仓库不存在: {self._project_path}")
                raise ValueError(f"GitLab仓库不存在")
            else:
                logger.error(f"获取GitLab仓库信息失败: {str(e)}")
                raise ValueError(f"获取GitLab仓库信息失败: HTTP {e.response.status_code}")
        except Exception as e:
            logger.error(f"GitLab API请求失败: {str(e)}")
            # 返回基本信息
            return {
                "url": self._repo_url,
                "type": "gitlab",
                "repo_name": self._repo_name,
                "project_path": self._project_path
            }
    
    @property
    def repo_url(self) -> str:
        """获取仓库URL"""
        return self._repo_url
    
    @property
    def provider_name(self) -> str:
        """获取提供商名称"""
        return "gitlab" 