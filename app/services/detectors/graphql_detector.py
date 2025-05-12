#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GraphQL API检测器 - 检测GraphQL API
"""

import re
import uuid
from pathlib import Path
from typing import List

from app.models.api import (GraphQLAPI, GraphQLMutation, GraphQLQuery,
                           GraphQLType)
from app.services.detectors.base_detector import BaseDetector


class GraphQLDetector(BaseDetector):
    """GraphQL API检测器"""
    
    def __init__(self):
        """初始化GraphQL API检测器"""
        super().__init__()
        self.patterns = {
            'graphql_type': re.compile(r'type\s+(?P<type>[A-Za-z0-9_]+)'),
            'graphql_query': re.compile(r'extend type Query {(?P<queries>.*?)}', re.DOTALL),
            'graphql_mutation': re.compile(r'extend type Mutation {(?P<mutations>.*?)}', re.DOTALL),
        }
        
    def detect(self, content: str, file_path: Path, codebase_path: Path) -> List[GraphQLAPI]:
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
                source_file=self._get_relative_path(file_path, codebase_path),
                source_line=1  # 默认第一行
            )
            
            apis.append(api)
        
        return apis 