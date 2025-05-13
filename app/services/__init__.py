#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
服务包 - 提供各种应用服务
"""

# 导出所有服务模块
from app.services import git_providers
from app.services import detectors
from app.services import file_service
from app.services import git_service
from app.services import detector_service

# 导出服务实例
from app.services.detector_service import detector_service

__all__ = [
    'git_providers',
    'detectors',
    'file_service',
    'git_service',
    'detector_service',
] 