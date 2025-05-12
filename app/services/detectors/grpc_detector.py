#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
gRPC API检测器 - 检测gRPC服务
"""

import re
import uuid
from pathlib import Path
from typing import List

from app.models.api import GRPCMethod, GRPCService, MessageType
from app.services.detectors.base_detector import BaseDetector


class GRPCDetector(BaseDetector):
    """gRPC API检测器"""
    
    def __init__(self):
        """初始化gRPC API检测器"""
        super().__init__()
        self.patterns = {
            'grpc_service': re.compile(r'service\s+(?P<service>[A-Za-z0-9_]+)\s*{'),
            'grpc_method': re.compile(r'rpc\s+(?P<method>[A-Za-z0-9_]+)\s*\(\s*(?P<input>[A-Za-z0-9_\.]+)\s*\)\s*returns\s*\(\s*(?P<o>[A-Za-z0-9_\.]+)\s*\)'),
        }
        
    def detect(self, content: str, file_path: Path, codebase_path: Path) -> List[GRPCService]:
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
                source_file=self._get_relative_path(file_path, codebase_path),
                source_line=content[:service_start].count('\n') + 1
            )
            
            services.append(service)
        
        return services 