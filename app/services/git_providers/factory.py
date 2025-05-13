#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Git提供商工厂 - 根据仓库URL选择合适的提供商
"""

from typing import Type, List

from app.services.git_providers.base import GitProvider
from app.services.git_providers.github import GitHubProvider
from app.services.git_providers.gitlab import GitLabProvider
from app.services.git_providers.bitbucket import BitbucketProvider
from app.services.git_providers.generic import GenericGitProvider
from app.utils.logger import logger


class GitProviderFactory:
    """Git提供商工厂类"""
    
    # 按优先级排序的提供商列表
    _providers: List[Type[GitProvider]] = [
        GitHubProvider,
        GitLabProvider,
        BitbucketProvider,
        GenericGitProvider  # 通用提供商作为后备
    ]
    
    @classmethod
    async def create_provider(cls, repo_url: str) -> GitProvider:
        """
        根据仓库URL创建合适的Git提供商
        
        Args:
            repo_url: 仓库URL
            
        Returns:
            合适的Git提供商实例
        """
        # 遍历所有提供商，找到第一个可以处理该URL的提供商
        for provider_class in cls._providers:
            try:
                if await provider_class.can_handle(repo_url):
                    provider = provider_class(repo_url)
                    logger.info(f"使用 {provider.provider_name} 提供商处理仓库: {repo_url}")
                    return provider
            except Exception as e:
                logger.warning(f"尝试使用 {provider_class.__name__} 时出错: {str(e)}")
                continue
        
        # 如果没有找到合适的提供商，使用通用提供商
        logger.info(f"没有找到专用提供商，使用通用Git提供商处理仓库: {repo_url}")
        return GenericGitProvider(repo_url)
    
    @classmethod
    def register_provider(cls, provider: Type[GitProvider]) -> None:
        """
        注册新的Git提供商
        
        Args:
            provider: 提供商类
        """
        if provider not in cls._providers:
            # 插入到通用提供商之前
            cls._providers.insert(-1, provider)
            logger.info(f"注册新的Git提供商: {provider.__name__}")


# 导出工厂类
__all__ = ['GitProviderFactory'] 