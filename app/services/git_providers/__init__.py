#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Git提供商包 - 提供不同Git服务的实现
"""

from app.services.git_providers.base import GitProvider
from app.services.git_providers.github import GitHubProvider
from app.services.git_providers.gitlab import GitLabProvider
from app.services.git_providers.bitbucket import BitbucketProvider
from app.services.git_providers.generic import GenericGitProvider
from app.services.git_providers.factory import GitProviderFactory

# 导出所有提供商
__all__ = [
    'GitProvider',
    'GitHubProvider',
    'GitLabProvider',
    'BitbucketProvider',
    'GenericGitProvider',
    'GitProviderFactory',
] 