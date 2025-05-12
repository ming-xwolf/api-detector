#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
REST API检测器 - 检测REST API端点
"""

import re
import uuid
from pathlib import Path
from typing import List

from app.models.api import HttpMethod, RESTEndpoint
from app.services.detectors.base_detector import BaseDetector


class RESTDetector(BaseDetector):
    """REST API检测器"""
    
    def __init__(self):
        """初始化REST API检测器"""
        super().__init__()
        self.patterns = {
            'fastapi_route': re.compile(r'@(app|router|blueprint)\.(?P<method>get|post|put|delete|patch|options|head)\s*\(\s*[\'"](?P<path>[^\'"]+)[\'"]'),
            'flask_route': re.compile(r'@(app|blueprint)\.route\s*\(\s*[\'"](?P<path>[^\'"]+)[\'"](\s*,\s*methods=\[(?P<methods>[^\]]+)\])?'),
            'express_route': re.compile(r'(app|router)\.(get|post|put|delete|patch|options|all)\s*\(\s*[\'"](?P<path>[^\'"]+)[\'"]'),
            'spring_route': re.compile(r'@(GetMapping|PostMapping|PutMapping|DeleteMapping|RequestMapping)(\s*\(\s*[\'"](?P<path>[^\'"]+)[\'"])?'),
        }
        
    def detect(self, content: str, file_path: Path, codebase_path: Path) -> List[RESTEndpoint]:
        """
        检测REST API端点
        
        Args:
            content: 文件内容
            file_path: 文件路径
            codebase_path: 代码库路径
            
        Returns:
            REST API端点列表
        """
        endpoints = []
        
        # 检测FastAPI路由
        for match in self.patterns['fastapi_route'].finditer(content):
            method = match.group('method').upper()
            path = match.group('path')
            
            endpoint = RESTEndpoint(
                id=str(uuid.uuid4()),
                name=f"{method} {path}",
                path=path,
                method=HttpMethod(method.upper()),
                source_file=self._get_relative_path(file_path, codebase_path),
                source_line=self._get_line_number(content, match.start())
            )
            
            endpoints.append(endpoint)
            
        # 检测Flask路由
        for match in self.patterns['flask_route'].finditer(content):
            path = match.group('path')
            methods_str = match.group('methods')
            
            # 如果没有指定方法，默认为GET
            if not methods_str:
                methods = ["GET"]
            else:
                methods = re.findall(r'[\'"]([A-Z]+)[\'"]', methods_str)
            
            for method in methods:
                endpoint = RESTEndpoint(
                    id=str(uuid.uuid4()),
                    name=f"{method} {path}",
                    path=path,
                    method=HttpMethod(method.upper()),
                    source_file=self._get_relative_path(file_path, codebase_path),
                    source_line=self._get_line_number(content, match.start())
                )
                
                endpoints.append(endpoint)
                
        # 检测Express路由
        for match in self.patterns['express_route'].finditer(content):
            method = match.group(2).upper()
            path = match.group('path')
            
            endpoint = RESTEndpoint(
                id=str(uuid.uuid4()),
                name=f"{method} {path}",
                path=path,
                method=HttpMethod(method.upper() if method != 'ALL' else 'GET'),
                source_file=self._get_relative_path(file_path, codebase_path),
                source_line=self._get_line_number(content, match.start())
            )
            
            endpoints.append(endpoint)
            
        # 检测Spring路由
        for match in self.patterns['spring_route'].finditer(content):
            mapping_type = match.group(1)
            path = match.group('path') or ''
            
            # 根据注解类型确定HTTP方法
            method_map = {
                'GetMapping': 'GET',
                'PostMapping': 'POST',
                'PutMapping': 'PUT',
                'DeleteMapping': 'DELETE',
                'RequestMapping': 'GET'  # 默认为GET
            }
            
            method = method_map.get(mapping_type, 'GET')
            
            endpoint = RESTEndpoint(
                id=str(uuid.uuid4()),
                name=f"{method} {path}",
                path=path,
                method=HttpMethod(method),
                source_file=self._get_relative_path(file_path, codebase_path),
                source_line=self._get_line_number(content, match.start())
            )
            
            endpoints.append(endpoint)
            
        return endpoints 