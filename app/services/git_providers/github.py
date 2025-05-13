#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GitHub提供商 - 处理GitHub仓库
"""

import os
import shutil
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional, Dict, Any

import git
import httpx

from app.core.config import settings
from app.services.git_providers.base import GitProvider
from app.utils.logger import logger


class GitHubProvider(GitProvider):
    """GitHub提供商实现"""
    
    def __init__(self, repo_url: str):
        """
        初始化GitHub提供商
        
        Args:
            repo_url: GitHub仓库URL
        """
        self._repo_url = repo_url
        self._parsed_url = urlparse(repo_url)
        self._path_parts = self._parsed_url.path.strip("/").split("/")
        
        if len(self._path_parts) < 2:
            raise ValueError(f"无效的GitHub仓库URL: {repo_url}")
            
        self._owner = self._path_parts[0]
        self._repo_name = self._path_parts[1].replace('.git', '')
    
    @classmethod
    async def can_handle(cls, repo_url: str) -> bool:
        """
        检查是否可以处理指定的仓库URL
        
        Args:
            repo_url: 仓库URL
            
        Returns:
            如果是GitHub URL则返回True，否则返回False
        """
        return "github.com" in repo_url.lower()
    
    async def get_default_branch(self) -> str:
        """
        获取仓库的默认分支
        
        Returns:
            默认分支名称
        """
        # 构建API URL
        api_url = f"{settings.GITHUB_API_URL}/repos/{self._owner}/{self._repo_name}"
        logger.debug(f"获取仓库默认分支: {api_url}")
        
        try:
            # 使用同步客户端请求GitHub API
            headers = {"Accept": "application/json"}
            
            # 检查是否有有效的令牌（不包含注释或空格）
            git_token = settings.GIT_TOKEN
            if git_token and git_token.strip() and not git_token.strip().startswith("#"):
                headers["Authorization"] = f"token {git_token.strip()}"
                
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                response = client.get(api_url, headers=headers)
                response.raise_for_status()
                
                repo_info = response.json()
                default_branch = repo_info.get("default_branch", "main")
                logger.info(f"仓库默认分支: {default_branch}")
                return default_branch
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"仓库不存在: {self._owner}/{self._repo_name}")
                raise ValueError(f"仓库不存在: {self._owner}/{self._repo_name}")
            else:
                logger.error(f"获取仓库信息失败: {str(e)}")
                raise ValueError(f"获取仓库信息失败: {str(e)}")
        except Exception as e:
            logger.error(f"获取仓库默认分支时出错: {str(e)}")
            # 如果无法获取默认分支，返回常见的默认分支名称
            return "main"
    
    async def download_zip(self, branch: Optional[str] = None) -> Path:
        """
        下载仓库的ZIP文件
        
        Args:
            branch: 分支名，如果为None则使用默认分支
            
        Returns:
            下载的ZIP文件路径
        """
        # 如果没有指定分支，获取默认分支
        if branch is None:
            branch = await self.get_default_branch()
            
        # 构建ZIP下载URL
        zip_url = f"https://github.com/{self._owner}/{self._repo_name}/archive/refs/heads/{branch}.zip"
        
        
        # 创建保存路径
        zip_file_path = Path(settings.TEMP_DIR) / f"github_{self._owner}_{self._repo_name}_{branch}.zip"
        
        # 确保目录存在
        zip_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 如果文件已存在，先删除
        if zip_file_path.exists():
            zip_file_path.unlink()
            
        logger.info(f"正在下载GitHub仓库ZIP: {self._repo_url} (分支: {branch})")
        
        try:
            # 设置请求头
            headers = {}
            
                
            # 下载ZIP文件
            with httpx.Client(timeout=60.0, follow_redirects=True) as client:
                with client.stream("GET", zip_url, headers=headers) as response:
                    response.raise_for_status()
                    
                    # 写入文件
                    with open(zip_file_path, "wb") as f:
                        for chunk in response.iter_bytes(chunk_size=8192):
                            f.write(chunk)
                            
            logger.info(f"GitHub仓库ZIP下载成功: {zip_file_path}")
            return zip_file_path
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"仓库或分支不存在: {self._owner}/{self._repo_name}/{branch}")
                raise ValueError(f"仓库或分支不存在: {self._owner}/{self._repo_name}/{branch}")
            else:
                logger.error(f"下载GitHub仓库ZIP失败: {str(e)}")
                raise ValueError(f"下载GitHub仓库ZIP失败: {str(e)}")
        except Exception as e:
            logger.error(f"下载GitHub仓库ZIP时出错: {str(e)}")
            raise ValueError(f"下载GitHub仓库ZIP时出错: {str(e)}")
    
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
            branch = await self.get_default_branch()
        
        # 创建临时目录
        clone_dir = Path(settings.TEMP_DIR) / f"github_{self._repo_name}_{branch}"
        
        # 如果目录已存在，先删除
        if clone_dir.exists():
            shutil.rmtree(clone_dir)
        
        # 创建目录
        clone_dir.mkdir(parents=True, exist_ok=True)
        
        # 构建克隆命令
        logger.info(f"正在克隆GitHub仓库: {self._repo_url} (分支: {branch})")
        
        # 处理认证信息
        auth_url = self._repo_url
        
        # 检查是否有有效的令牌（不包含注释或空格）
        git_token = settings.GIT_TOKEN
        if git_token and git_token.strip() and not git_token.strip().startswith("#"):
            auth_url = self._repo_url.replace('https://', f'https://oauth2:{git_token.strip()}@')
            logger.debug("使用GitHub令牌进行认证")
            
        try:
            # 克隆仓库
            git.Repo.clone_from(auth_url, clone_dir, branch=branch, depth=1)
            logger.info(f"仓库克隆成功: {clone_dir}")
            return clone_dir
        except git.exc.GitCommandError as e:
            logger.error(f"克隆仓库失败: {str(e)}")
            if "not found" in str(e).lower():
                # 可能是私有仓库或不存在
                raise ValueError(f"GitHub仓库未找到或需要访问权限。如果是私有仓库，请提供有效的GitHub令牌。")
            elif "could not read Username" in str(e):
                raise ValueError(f"需要访问权限克隆此GitHub仓库。请提供有效的GitHub令牌。")
            raise ValueError(f"克隆GitHub仓库失败: {str(e)}")
    
    async def get_repo_info(self) -> Dict[str, Any]:
        """
        获取仓库的基本信息
        
        Returns:
            包含仓库信息的字典
        """
        try:
            # 构建API URL
            api_url = f"{settings.GITHUB_API_URL}/repos/{self._owner}/{self._repo_name}"
            logger.debug(f"GitHub API URL: {api_url}")
            
            # 创建一个新的httpx客户端
            limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)
            timeout = httpx.Timeout(10.0, connect=5.0)
            
            async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
                # 设置最小化的请求头
                headers = {"Accept": "application/json"}
                
                # 检查是否有有效的令牌（不包含注释或空格）
                git_token = settings.GIT_TOKEN
                if git_token and git_token.strip() and not git_token.strip().startswith("#"):
                    headers["Authorization"] = f"token {git_token.strip()}"
                    
                # 发送请求
                response = await client.get(api_url, headers=headers)
                response.raise_for_status()
                
                # 解析响应
                repo_info = response.json()
                
                # 提取感兴趣的信息
                result = {
                    "url": self._repo_url,
                    "type": "github",
                    "repo_name": self._repo_name,
                    "owner": self._owner,
                    "name": repo_info.get("name", ""),
                    "full_name": repo_info.get("full_name", ""),
                    "description": repo_info.get("description", ""),
                    "default_branch": repo_info.get("default_branch", "main"),
                    "language": repo_info.get("language", ""),
                    "stars": repo_info.get("stargazers_count", 0),
                    "forks": repo_info.get("forks_count", 0),
                    "open_issues": repo_info.get("open_issues_count", 0),
                    "created_at": repo_info.get("created_at", ""),
                    "updated_at": repo_info.get("updated_at", ""),
                    "owner_type": repo_info.get("owner", {}).get("type", "")
                }
                
                return result
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"仓库不存在: {self._repo_url}")
                raise ValueError(f"GitHub仓库不存在")
            else:
                logger.error(f"获取仓库信息失败: {str(e)}")
                raise ValueError(f"获取GitHub仓库信息失败: HTTP {e.response.status_code}")
        except Exception as e:
            logger.error(f"GitHub API请求失败: {str(e)}")
            # 返回基本信息
            return {
                "url": self._repo_url,
                "type": "github",
                "repo_name": self._repo_name,
                "owner": self._owner
            }
    
    @property
    def repo_url(self) -> str:
        """获取仓库URL"""
        return self._repo_url
    
    @property
    def provider_name(self) -> str:
        """获取提供商名称"""
        return "github" 