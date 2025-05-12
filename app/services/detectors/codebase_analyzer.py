#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
代码库分析器 - 分析代码库中的API
"""

import os
from pathlib import Path
from typing import List

from app.models.api import AnalysisResult
from app.services.detectors.graphql_detector import GraphQLDetector
from app.services.detectors.grpc_detector import GRPCDetector
from app.services.detectors.openapi_detector import OpenAPIDetector
from app.services.detectors.rest_detector import RESTDetector
from app.services.detectors.websocket_detector import WebSocketDetector
from app.utils.logger import logger


class CodebaseAnalyzer:
    """代码库分析器"""
    
    def __init__(self):
        """初始化代码库分析器"""
        self.supported_extensions = {
            '.py', '.js', '.ts', '.java', '.go', '.rb', '.php', '.cs', '.proto',
            '.graphql', '.gql', '.yaml', '.yml', '.json'
        }
        
        # 初始化各类型检测器
        self.rest_detector = RESTDetector()
        self.websocket_detector = WebSocketDetector()
        self.grpc_detector = GRPCDetector()
        self.graphql_detector = GraphQLDetector()
        self.openapi_detector = OpenAPIDetector()
        
    async def analyze(self, codebase_path: Path, source: str, project_name: str = None) -> AnalysisResult:
        """
        分析代码库
        
        Args:
            codebase_path: 代码库路径
            source: 源类型 ('zip', 'github', 'local')
            project_name: 项目名称
            
        Returns:
            API分析结果
        """
        if not project_name:
            project_name = codebase_path.name
            
        logger.info(f"开始分析代码库: {codebase_path}")
        
        # 初始化结果
        result = AnalysisResult(
            project_name=project_name,
            source=source,
            source_info={"path": str(codebase_path)}
        )
        
        # 检测OpenAPI规范文件
        openapi_specs = await self.openapi_detector.detect(codebase_path)
        if openapi_specs:
            result.apis.extend(openapi_specs)
            result.stats["OpenAPI"] = len(openapi_specs)
        
        # 遍历代码库
        code_files = self._collect_code_files(codebase_path)
        
        # 检测各种API
        rest_endpoints = []
        websocket_apis = []
        grpc_services = []
        graphql_apis = []
        
        for file_path in code_files:
            try:
                # 读取文件内容
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # 检测REST API
                if file_path.suffix in ['.py', '.js', '.ts', '.java', '.php', '.rb', '.cs']:
                    endpoints = self.rest_detector.detect(content, file_path, codebase_path)
                    rest_endpoints.extend(endpoints)
                
                # 检测WebSocket API
                if file_path.suffix in ['.py', '.js', '.ts']:
                    ws_apis = self.websocket_detector.detect(content, file_path, codebase_path)
                    websocket_apis.extend(ws_apis)
                
                # 检测gRPC服务
                if file_path.suffix == '.proto':
                    services = self.grpc_detector.detect(content, file_path, codebase_path)
                    grpc_services.extend(services)
                
                # 检测GraphQL API
                if file_path.suffix in ['.graphql', '.gql'] or (
                    file_path.suffix in ['.js', '.ts'] and ('graphql' in content or 'apollo' in content)
                ):
                    apis = self.graphql_detector.detect(content, file_path, codebase_path)
                    graphql_apis.extend(apis)
                    
            except Exception as e:
                logger.error(f"分析文件时出错 {file_path}: {str(e)}", exc_info=True)
                result.errors.append({
                    "file": str(file_path.relative_to(codebase_path)),
                    "message": str(e)
                })
        
        # 添加检测到的API到结果中
        result.apis.extend(rest_endpoints)
        result.apis.extend(websocket_apis)
        result.apis.extend(grpc_services)
        result.apis.extend(graphql_apis)
        
        # 更新统计信息
        result.stats["REST"] = len(rest_endpoints)
        result.stats["WebSocket"] = len(websocket_apis)
        result.stats["gRPC"] = len(grpc_services)
        result.stats["GraphQL"] = len(graphql_apis)
        result.stats["total"] = len(result.apis)
        
        logger.info(f"代码库分析完成: {project_name}, 共找到 {result.stats['total']} 个API")
        return result
        
    def _collect_code_files(self, codebase_path: Path) -> List[Path]:
        """收集代码文件"""
        code_files = []
        for root, _, files in os.walk(codebase_path):
            # 跳过隐藏目录和常见的非代码目录
            if any(part.startswith('.') for part in Path(root).parts) or \
               any(part in ['node_modules', 'venv', '.git', '.idea', '__pycache__'] for part in Path(root).parts):
                continue
                
            for file in files:
                file_path = Path(root) / file
                
                # 检查文件扩展名
                if file_path.suffix not in self.supported_extensions:
                    continue
                
                # 跳过常见的第三方库和构建文件
                if 'vendor' in file_path.parts or 'dist' in file_path.parts or 'build' in file_path.parts:
                    continue
                    
                code_files.append(file_path)
                
        return code_files 