#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
通用Git提供商 - 处理标准Git仓库
"""

import os
import shutil
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional, Dict, Any

import git

from app.core.config import settings
from app.services.git_providers.base import GitProvider
from app.utils.logger import logger


class GenericGitProvider(GitProvider):
    """通用Git提供商实现"""
    
    def __init__(self, repo_url: str):
        """
        初始化通用Git提供商
        
        Args:
            repo_url: Git仓库URL
        """
        self._repo_url = repo_url
        self._parsed_url = urlparse(repo_url)
        self._path_parts = self._parsed_url.path.strip("/").split("/")
        self._repo_name = self._path_parts[-1].replace('.git', '')
    
    @classmethod
    async def can_handle(cls, repo_url: str) -> bool:
        """
        检查是否可以处理指定的仓库URL
        
        Args:
            repo_url: 仓库URL
            
        Returns:
            总是返回True，作为通用处理器
        """
        # 通用处理器可以处理任何URL
        return True
    
    async def get_default_branch(self) -> str:
        """
        获取仓库的默认分支
        
        Returns:
            默认分支名称
        """
        try:
            # 创建临时目录用于检查
            temp_dir = Path(settings.TEMP_DIR) / f"temp_branch_check"
            
            # 如果目录已存在，先删除
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            
            # 使用git命令进行浅克隆，只获取HEAD引用
            logger.debug(f"正在检查仓库默认分支: {self._repo_url}")
            
            # 克隆仓库，只获取最小信息
            repo = git.Repo.init(temp_dir)
            origin = repo.create_remote('origin', self._repo_url)
            origin.fetch(depth=1)
            
            # 获取默认分支（HEAD指向的分支）
            for ref in repo.references:
                if ref.name == 'origin/HEAD':
                    # 解析引用的目标，通常是 'refs/remotes/origin/main' 形式
                    target = ref.reference.name
                    # 提取分支名称部分
                    default_branch = target.split('/')[-1]
                    logger.info(f"仓库默认分支: {default_branch}")
                    return default_branch
                    
            # 如果无法确定默认分支，尝试常见分支名
            logger.warning("无法确定默认分支，将尝试常见分支名")
            return "main"
                
        except Exception as e:
            logger.error(f"获取仓库默认分支时出错: {str(e)}")
            # 如果无法获取默认分支，返回常见的默认分支名称
            return "main"
        finally:
            # 清理临时目录
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
    
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
        import zipfile
        
        # 克隆仓库到临时目录
        temp_clone_dir = None
        
        try:
            # 克隆仓库
            temp_clone_dir = await self.clone_repository(branch)
            
            # 创建ZIP文件路径
            zip_file_path = Path(settings.TEMP_DIR) / f"git_{self._repo_name}_{branch}.zip"
            
            # 如果文件已存在，先删除
            if zip_file_path.exists():
                zip_file_path.unlink()
                
            logger.info(f"正在创建仓库ZIP文件: {self._repo_url} (分支: {branch})")
            
            # 创建ZIP文件
            with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 遍历克隆目录中的所有文件和子目录
                for root, _, files in os.walk(temp_clone_dir):
                    # 跳过.git目录
                    if '.git' in Path(root).parts:
                        continue
                        
                    # 添加文件到ZIP
                    for file in files:
                        file_path = Path(root) / file
                        # 计算相对路径，作为ZIP中的路径
                        relative_path = file_path.relative_to(temp_clone_dir)
                        # 添加到ZIP
                        zipf.write(file_path, relative_path)
                        
            logger.info(f"仓库ZIP文件创建成功: {zip_file_path}")
            return zip_file_path
            
        except Exception as e:
            logger.error(f"创建仓库ZIP文件时出错: {str(e)}")
            raise ValueError(f"创建仓库ZIP文件时出错: {str(e)}")
        finally:
            # 清理临时目录
            if temp_clone_dir and Path(temp_clone_dir).exists():
                shutil.rmtree(temp_clone_dir)
    
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
        clone_dir = Path(settings.TEMP_DIR) / f"git_{self._repo_name}_{branch}"
        
        # 如果目录已存在，先删除
        if clone_dir.exists():
            shutil.rmtree(clone_dir)
        
        # 创建目录
        clone_dir.mkdir(parents=True, exist_ok=True)
        
        # 构建克隆命令
        logger.info(f"正在克隆仓库: {self._repo_url} (分支: {branch})")
        
        # 处理认证信息
        auth_url = self._repo_url
        
        # 检查是否有提供令牌
        if settings.GIT_TOKEN:
            # 通用方式
            auth_url = self._repo_url.replace('https://', f'https://{settings.GIT_TOKEN}@')
            logger.debug("使用Git令牌进行认证")
            
        try:
            # 克隆仓库
            git.Repo.clone_from(auth_url, clone_dir, branch=branch, depth=1)
            logger.info(f"仓库克隆成功: {clone_dir}")
            return clone_dir
        except git.exc.GitCommandError as e:
            logger.error(f"克隆仓库失败: {str(e)}")
            if "not found" in str(e).lower():
                # 可能是私有仓库或不存在
                raise ValueError(f"仓库未找到或需要访问权限。如果是私有仓库，请提供有效的Git令牌。")
            elif "could not read Username" in str(e):
                raise ValueError(f"需要访问权限克隆此仓库。请提供有效的Git令牌。")
            raise ValueError(f"克隆仓库失败: {str(e)}")
    
    async def get_repo_info(self) -> Dict[str, Any]:
        """
        获取仓库的基本信息
        
        Returns:
            包含仓库信息的字典
        """
        try:
            # 仓库域名
            domain = self._parsed_url.netloc
            
            # 仓库路径
            path = self._parsed_url.path.strip("/").strip(".git")
            path_parts = path.split("/")
            
            # 获取仓库名
            repo_name = self._repo_name
            
            # 获取所有者/组织（如果有）
            owner = path_parts[-2] if len(path_parts) > 1 else None
            
            # 构建结果
            result = {
                "url": self._repo_url,
                "domain": domain,
                "type": "git",
                "repo_name": repo_name
            }
            
            if owner:
                result["owner"] = owner
                
            return result
            
        except Exception as e:
            logger.error(f"解析仓库信息时出错: {str(e)}")
            return {
                "url": self._repo_url,
                "type": "unknown"
            }
    
    @property
    def repo_url(self) -> str:
        """获取仓库URL"""
        return self._repo_url
    
    @property
    def provider_name(self) -> str:
        """获取提供商名称"""
        return "generic" 