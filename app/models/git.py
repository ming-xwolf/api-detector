#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Git模型 - 定义Git仓库相关的数据模型
"""

from typing import Optional
from pydantic import BaseModel, HttpUrl


class GitRepository(BaseModel):
    """Git仓库请求模型"""
    repo_url: HttpUrl
    branch: Optional[str] = None  # 可选参数，如果不提供则使用仓库默认分支 