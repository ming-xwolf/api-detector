#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置模块 - 从.env文件加载应用配置
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

from pydantic import BaseModel, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用程序设置模型"""
    
    # 应用设置
    APP_NAME: str = "API检测器"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"  # development | production | testing
    DEBUG: bool = True
    
    # 服务器设置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    RELOAD: bool = True  # 仅在开发环境使用
    
    # GitHub相关设置
    GITHUB_TOKEN: Optional[str] = None  # 如需更高API访问限制，请设置GitHub令牌
    
    # 存储设置
    UPLOAD_DIR: str = "./data/uploads"
    TEMP_DIR: str = "./data/temp"
    RESULTS_DIR: str = "./data/results"
    TEMP_RETENTION_DAYS: int = 1  # 临时文件保留天数
    
    # 安全设置
    CORS_ORIGINS: str = "*"  # CORS允许的来源
    API_KEY: Optional[str] = None  # 如需API认证，请设置此项
    
    # 日志设置
    LOG_LEVEL: str = "INFO"  # DEBUG | INFO | WARNING | ERROR | CRITICAL
    LOG_FILE: str = "./logs/api-detector.log"
    
    def setup_directories(self) -> None:
        """确保所有必要的目录都存在"""
        for dir_path in [self.UPLOAD_DIR, self.TEMP_DIR, self.RESULTS_DIR, os.path.dirname(self.LOG_FILE)]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=True,
        env_file_exists_ok=True,  # 即使.env文件不存在也不会报错
        env_ignore_undefined=True,  # 忽略未定义的环境变量
    )


# 创建设置实例
settings = Settings()

# 在导入时设置目录
settings.setup_directories() 