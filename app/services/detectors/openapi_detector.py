#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OpenAPI规范检测器 - 检测OpenAPI规范文件
"""

import json
import uuid
from pathlib import Path
from typing import List

import yaml

from app.models.api import OpenAPISpec
from app.services.detectors.base_detector import BaseDetector
from app.utils.logger import logger


class OpenAPIDetector(BaseDetector):
    """OpenAPI规范检测器"""
    
    def __init__(self):
        """初始化OpenAPI规范检测器"""
        super().__init__()
        
    async def detect(self, codebase_path: Path) -> List[OpenAPISpec]:
        """
        检测OpenAPI规范文件
        
        Args:
            codebase_path: 代码库路径
            
        Returns:
            OpenAPI规范列表
        """
        specs = []
        
        # 寻找可能的OpenAPI规范文件
        openapi_patterns = [
            '**/openapi.yaml', '**/openapi.yml', '**/openapi.json',
            '**/swagger.yaml', '**/swagger.yml', '**/swagger.json',
            '**/api-spec.yaml', '**/api-spec.yml', '**/api-spec.json'
        ]
        
        for pattern in openapi_patterns:
            for file_path in Path(codebase_path).glob(pattern):
                try:
                    # 读取文件内容
                    with open(file_path, 'r', encoding='utf-8') as f:
                        if file_path.suffix in ['.yaml', '.yml']:
                            content = yaml.safe_load(f)
                        else:  # .json
                            content = json.load(f)
                    
                    # 验证是否为OpenAPI规范
                    if ('swagger' in content or 'openapi' in content) and 'paths' in content:
                        version = content.get('openapi', content.get('swagger', 'unknown'))
                        
                        spec = OpenAPISpec(
                            id=str(uuid.uuid4()),
                            name=content.get('info', {}).get('title', file_path.stem),
                            description=content.get('info', {}).get('description'),
                            version=version,
                            info=content.get('info', {}),
                            paths=content.get('paths', {}),
                            components=content.get('components'),
                            source_file=self._get_relative_path(file_path, codebase_path)
                        )
                        
                        specs.append(spec)
                        logger.info(f"检测到OpenAPI规范: {file_path.relative_to(codebase_path)}")
                        
                except Exception as e:
                    logger.error(f"解析OpenAPI规范文件时出错 {file_path}: {str(e)}")
        
        return specs 