#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API检测服务 - 检测代码库中的API
"""

import os
import re
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urlparse

import yaml
from fastapi import UploadFile

from app.core.config import settings
from app.models.api import (APIBase, APIType, AnalysisResult, GraphQLAPI,
                           GRPCMethod, GRPCService, HttpMethod, MessageType,
                           OpenAPISpec, Parameter, RESTEndpoint, Response,
                           WebSocketAPI)
from app.services.file_service import cleanup_temp_files, extract_zip, save_upload_file
from app.services.github_service import download_repository_zip
from app.utils.logger import logger


class APIDetectorService:
    """API检测服务"""
    
    def __init__(self):
        """初始化检测服务"""
        self.supported_extensions = {
            '.py', '.js', '.ts', '.java', '.go', '.rb', '.php', '.cs', '.proto',
            '.graphql', '.gql', '.yaml', '.yml', '.json'
        }
        
        # 正则表达式模式
        self.patterns = {
            # REST API模式
            'fastapi_route': re.compile(r'@(app|router|blueprint)\.(?P<method>get|post|put|delete|patch|options|head)\s*\(\s*[\'"](?P<path>[^\'"]+)[\'"]'),
            'flask_route': re.compile(r'@(app|blueprint)\.route\s*\(\s*[\'"](?P<path>[^\'"]+)[\'"](\s*,\s*methods=\[(?P<methods>[^\]]+)\])?'),
            'express_route': re.compile(r'(app|router)\.(get|post|put|delete|patch|options|all)\s*\(\s*[\'"](?P<path>[^\'"]+)[\'"]'),
            'spring_route': re.compile(r'@(GetMapping|PostMapping|PutMapping|DeleteMapping|RequestMapping)(\s*\(\s*[\'"](?P<path>[^\'"]+)[\'"])?'),
            
            # WebSocket模式
            'websocket_route': re.compile(r'@(app|router)\.websocket\s*\(\s*[\'"](?P<path>[^\'"]+)[\'"]'),
            'socketio': re.compile(r'@?socketio\.(on|event)\s*\(\s*[\'"](?P<event>[^\'"]+)[\'"]'),
            
            # gRPC模式
            'grpc_service': re.compile(r'service\s+(?P<service>[A-Za-z0-9_]+)\s*{'),
            'grpc_method': re.compile(r'rpc\s+(?P<method>[A-Za-z0-9_]+)\s*\(\s*(?P<input>[A-Za-z0-9_\.]+)\s*\)\s*returns\s*\(\s*(?P<output>[A-Za-z0-9_\.]+)\s*\)'),
            
            # GraphQL模式
            'graphql_type': re.compile(r'type\s+(?P<type>[A-Za-z0-9_]+)'),
            'graphql_query': re.compile(r'extend type Query {(?P<queries>.*?)}', re.DOTALL),
            'graphql_mutation': re.compile(r'extend type Mutation {(?P<mutations>.*?)}', re.DOTALL),
        }
    
    async def detect_from_upload(self, file: UploadFile) -> AnalysisResult:
        """
        从上传的ZIP文件中检测API
        
        Args:
            file: 上传的ZIP文件
            
        Returns:
            API分析结果
        """
        try:
            # 保存上传文件
            zip_path = await save_upload_file(file)
            
            # 解压ZIP文件
            extract_dir = await extract_zip(zip_path)
            
            # 分析代码库
            result = await self._analyze_codebase(extract_dir, f"zip:{file.filename}")
            
            # 清理临时文件
            cleanup_temp_files(zip_path)
            
            return result
        except Exception as e:
            logger.error(f"从ZIP文件检测API时出错: {str(e)}", exc_info=True)
            # 创建包含错误信息的结果
            return AnalysisResult(
                project_name=file.filename,
                source="zip",
                source_info={"filename": file.filename},
                errors=[{"message": str(e)}]
            )
    
    async def detect_from_github(self, repo_url: str, branch: str = None) -> AnalysisResult:
        """
        从GitHub仓库中检测API
        
        Args:
            repo_url: GitHub仓库URL
            branch: 分支名，如果为None则使用仓库默认分支
            
        Returns:
            API分析结果
        """
        try:
            # 确保repo_url是字符串类型
            repo_url_str = str(repo_url)
            
            # 解析仓库名称
            parsed_url = urlparse(repo_url_str)
            path_parts = parsed_url.path.strip("/").split("/")
            
            if len(path_parts) < 2:
                raise ValueError(f"无效的GitHub仓库URL: {repo_url_str}")
                
            owner, repo_name = path_parts[:2]
            repo_name = repo_name.replace(".git", "")
            project_name = f"{owner}/{repo_name}"
            
            # 下载仓库ZIP文件
            branch_info = f", 分支: {branch}" if branch else " (使用默认分支)"
            logger.info(f"开始下载GitHub仓库: {project_name}{branch_info}")
            repo_dir = await download_repository_zip(repo_url_str, branch)
            
            # 分析代码库
            result = await self._analyze_codebase(
                repo_dir, 
                "github",
                project_name
            )
            
            # 添加仓库信息
            result.source_info = {
                "repo_url": repo_url_str,
                "branch": branch or "默认分支",
                "owner": owner,
                "repo": repo_name
            }
            
            # 清理临时文件
            cleanup_temp_files(repo_dir)
            
            return result
        except Exception as e:
            logger.error(f"从GitHub仓库检测API时出错: {str(e)}", exc_info=True)
            
            # 安全地获取项目名称
            try:
                parsed_url = urlparse(str(repo_url))
                path_parts = parsed_url.path.strip("/").split("/")
                if len(path_parts) >= 2:
                    owner, repo_name = path_parts[:2]
                    project_name = f"{owner}/{repo_name}"
                else:
                    project_name = "unknown-repo"
            except:
                project_name = "unknown-repo"
                
            # 创建包含错误信息的结果
            return AnalysisResult(
                project_name=project_name,
                source="github",
                source_info={"repo_url": str(repo_url), "branch": branch or "默认分支"},
                errors=[{"message": str(e)}]
            )
    
    async def _analyze_codebase(self, codebase_path: Path, source: str, project_name: str = None) -> AnalysisResult:
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
        openapi_specs = await self._detect_openapi_specs(codebase_path)
        if openapi_specs:
            result.apis.extend(openapi_specs)
            result.stats["OpenAPI"] = len(openapi_specs)
        
        # 遍历代码库
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
                    endpoints = self._detect_rest_endpoints(content, file_path, codebase_path)
                    rest_endpoints.extend(endpoints)
                
                # 检测WebSocket API
                if file_path.suffix in ['.py', '.js', '.ts']:
                    ws_apis = self._detect_websocket_apis(content, file_path, codebase_path)
                    websocket_apis.extend(ws_apis)
                
                # 检测gRPC服务
                if file_path.suffix == '.proto':
                    services = self._detect_grpc_services(content, file_path, codebase_path)
                    grpc_services.extend(services)
                
                # 检测GraphQL API
                if file_path.suffix in ['.graphql', '.gql'] or (
                    file_path.suffix in ['.js', '.ts'] and ('graphql' in content or 'apollo' in content)
                ):
                    apis = self._detect_graphql_apis(content, file_path, codebase_path)
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
    
    async def _detect_openapi_specs(self, codebase_path: Path) -> List[OpenAPISpec]:
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
                            import json
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
                            source_file=str(file_path.relative_to(codebase_path))
                        )
                        
                        specs.append(spec)
                        logger.info(f"检测到OpenAPI规范: {file_path.relative_to(codebase_path)}")
                        
                except Exception as e:
                    logger.error(f"解析OpenAPI规范文件时出错 {file_path}: {str(e)}")
        
        return specs
    
    def _detect_rest_endpoints(self, content: str, file_path: Path, codebase_path: Path) -> List[RESTEndpoint]:
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
                source_file=str(file_path.relative_to(codebase_path)),
                source_line=content[:match.start()].count('\n') + 1
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
                    source_file=str(file_path.relative_to(codebase_path)),
                    source_line=content[:match.start()].count('\n') + 1
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
                source_file=str(file_path.relative_to(codebase_path)),
                source_line=content[:match.start()].count('\n') + 1
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
                source_file=str(file_path.relative_to(codebase_path)),
                source_line=content[:match.start()].count('\n') + 1
            )
            
            endpoints.append(endpoint)
            
        return endpoints
    
    def _detect_websocket_apis(self, content: str, file_path: Path, codebase_path: Path) -> List[WebSocketAPI]:
        """
        检测WebSocket API
        
        Args:
            content: 文件内容
            file_path: 文件路径
            codebase_path: 代码库路径
            
        Returns:
            WebSocket API列表
        """
        apis = []
        
        # 检测WebSocket路由
        for match in self.patterns['websocket_route'].finditer(content):
            path = match.group('path')
            
            api = WebSocketAPI(
                id=str(uuid.uuid4()),
                name=f"WebSocket {path}",
                endpoint=path,
                source_file=str(file_path.relative_to(codebase_path)),
                source_line=content[:match.start()].count('\n') + 1
            )
            
            apis.append(api)
            
        # 检测Socket.IO事件
        events = set()
        for match in self.patterns['socketio'].finditer(content):
            event = match.group('event')
            events.add(event)
            
        if events:
            api = WebSocketAPI(
                id=str(uuid.uuid4()),
                name=f"SocketIO {file_path.stem}",
                endpoint="/socket.io",  # Socket.IO的默认端点
                events=list(events),
                source_file=str(file_path.relative_to(codebase_path)),
                source_line=1  # 默认第一行
            )
            
            apis.append(api)
            
        return apis
    
    def _detect_grpc_services(self, content: str, file_path: Path, codebase_path: Path) -> List[GRPCService]:
        """
        检测gRPC服务
        
        Args:
            content: 文件内容
            file_path: 文件路径
            codebase_path: 代码库路径
            
        Returns:
            gRPC服务列表
        """
        services = []
        
        # 检测服务定义
        service_matches = list(self.patterns['grpc_service'].finditer(content))
        
        for svc_match in service_matches:
            service_name = svc_match.group('service')
            service_start = svc_match.start()
            
            # 查找服务定义的结束位置（下一个花括号）
            service_content = content[service_start:]
            brace_count = 0
            service_end = len(service_content)
            
            for i, char in enumerate(service_content):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        service_end = i + 1
                        break
            
            # 提取服务内容
            service_block = service_content[:service_end]
            
            # 查找方法定义
            methods = []
            for method_match in self.patterns['grpc_method'].finditer(service_block):
                method_name = method_match.group('method')
                input_type = method_match.group('input')
                output_type = method_match.group('output')
                
                # 检查是否为流式
                streaming = 'stream' in service_block[method_match.start()-10:method_match.end()+10]
                
                method = GRPCMethod(
                    name=method_name,
                    input_type=input_type,
                    output_type=output_type,
                    streaming=streaming
                )
                
                methods.append(method)
            
            # 提取消息类型（简化实现）
            message_types = []
            # 这里只是获取所有message类型名称，实际项目中可能需要更深入的解析
            for message_match in re.finditer(r'message\s+([A-Za-z0-9_]+)\s*{', content):
                message_name = message_match.group(1)
                message_types.append(MessageType(name=message_name))
            
            service = GRPCService(
                id=str(uuid.uuid4()),
                name=service_name,
                service_name=service_name,
                methods=methods,
                message_types=message_types,
                source_file=str(file_path.relative_to(codebase_path)),
                source_line=content[:service_start].count('\n') + 1
            )
            
            services.append(service)
        
        return services
    
    def _detect_graphql_apis(self, content: str, file_path: Path, codebase_path: Path) -> List[GraphQLAPI]:
        """
        检测GraphQL API
        
        Args:
            content: 文件内容
            file_path: 文件路径
            codebase_path: 代码库路径
            
        Returns:
            GraphQL API列表
        """
        apis = []
        
        # 检测GraphQL类型定义
        types = []
        for type_match in self.patterns['graphql_type'].finditer(content):
            type_name = type_match.group('type')
            if type_name not in ['Query', 'Mutation', 'Subscription']:
                types.append({"name": type_name})
        
        # 检测查询
        queries = []
        for query_match in self.patterns['graphql_query'].finditer(content):
            query_block = query_match.group('queries')
            for line in query_block.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    # 简化的解析，实际项目需要更复杂的解析
                    field_match = re.match(r'([A-Za-z0-9_]+)(?:\(.*\))?\s*:\s*([A-Za-z0-9_\[\]!]+)', line)
                    if field_match:
                        name, return_type = field_match.groups()
                        queries.append({"name": name, "return_type": return_type})
        
        # 检测变更
        mutations = []
        for mutation_match in self.patterns['graphql_mutation'].finditer(content):
            mutation_block = mutation_match.group('mutations')
            for line in mutation_block.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    # 简化的解析
                    field_match = re.match(r'([A-Za-z0-9_]+)(?:\(.*\))?\s*:\s*([A-Za-z0-9_\[\]!]+)', line)
                    if field_match:
                        name, return_type = field_match.groups()
                        mutations.append({"name": name, "return_type": return_type})
        
        # 如果找到GraphQL定义
        if types or queries or mutations:
            api = GraphQLAPI(
                id=str(uuid.uuid4()),
                name=f"GraphQL {file_path.stem}",
                types=[GraphQLType(**t) for t in types],
                queries=[GraphQLQuery(**q) for q in queries],
                mutations=[GraphQLMutation(**m) for m in mutations],
                source_file=str(file_path.relative_to(codebase_path)),
                source_line=1  # 默认第一行
            )
            
            apis.append(api)
        
        return apis


# 创建服务实例
detector_service = APIDetectorService() 