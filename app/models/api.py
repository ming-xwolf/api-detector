#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API模型 - 定义API检测时使用的数据模型
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field


class APIType(str, Enum):
    """API类型枚举"""
    REST = "REST"
    WEBSOCKET = "WebSocket"
    GRPC = "gRPC"
    GRAPHQL = "GraphQL"
    OPENAPI = "OpenAPI"


class HttpMethod(str, Enum):
    """HTTP方法枚举"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    OPTIONS = "OPTIONS"
    HEAD = "HEAD"


class Parameter(BaseModel):
    """参数模型"""
    name: str
    description: Optional[str] = None
    required: bool = False
    type: str
    location: str  # path, query, header, body, cookie
    default: Optional[str] = None


class Response(BaseModel):
    """响应模型"""
    status_code: int
    description: Optional[str] = None
    content_type: Optional[str] = None
    schema: Optional[Dict] = None


class APIBase(BaseModel):
    """API基础模型"""
    id: str
    name: str
    description: Optional[str] = None
    type: APIType
    detected_at: datetime = Field(default_factory=datetime.now)


class RESTEndpoint(APIBase):
    """REST API端点模型"""
    type: APIType = APIType.REST
    path: str
    method: HttpMethod
    parameters: List[Parameter] = []
    responses: Dict[int, Response] = {}
    authentication: Optional[str] = None
    deprecated: bool = False
    source_file: Optional[str] = None
    source_line: Optional[int] = None


class MessageSchema(BaseModel):
    """消息模式模型"""
    name: str
    description: Optional[str] = None
    fields: Dict[str, str] = {}  # 字段名 -> 类型


class WebSocketAPI(APIBase):
    """WebSocket API模型"""
    type: APIType = APIType.WEBSOCKET
    endpoint: str
    messages: List[MessageSchema] = []
    events: List[str] = []
    source_file: Optional[str] = None
    source_line: Optional[int] = None


class GRPCMethod(BaseModel):
    """gRPC方法模型"""
    name: str
    description: Optional[str] = None
    input_type: str
    output_type: str
    streaming: bool = False


class MessageType(BaseModel):
    """消息类型模型"""
    name: str
    fields: Dict[str, str] = {}  # 字段名 -> 类型


class GRPCService(APIBase):
    """gRPC服务模型"""
    type: APIType = APIType.GRPC
    service_name: str
    methods: List[GRPCMethod] = []
    message_types: List[MessageType] = []
    source_file: Optional[str] = None
    source_line: Optional[int] = None


class GraphQLType(BaseModel):
    """GraphQL类型模型"""
    name: str
    description: Optional[str] = None
    fields: Dict[str, str] = {}  # 字段名 -> 类型


class GraphQLQuery(BaseModel):
    """GraphQL查询模型"""
    name: str
    description: Optional[str] = None
    return_type: str
    arguments: Dict[str, str] = {}  # 参数名 -> 类型


class GraphQLMutation(BaseModel):
    """GraphQL变更模型"""
    name: str
    description: Optional[str] = None
    return_type: str
    arguments: Dict[str, str] = {}  # 参数名 -> 类型


class GraphQLSubscription(BaseModel):
    """GraphQL订阅模型"""
    name: str
    description: Optional[str] = None
    return_type: str
    arguments: Dict[str, str] = {}  # 参数名 -> 类型


class GraphQLAPI(APIBase):
    """GraphQL API模型"""
    type: APIType = APIType.GRAPHQL
    types: List[GraphQLType] = []
    queries: List[GraphQLQuery] = []
    mutations: List[GraphQLMutation] = []
    subscriptions: List[GraphQLSubscription] = []
    source_file: Optional[str] = None
    source_line: Optional[int] = None


class OpenAPISpec(APIBase):
    """OpenAPI规范模型"""
    type: APIType = APIType.OPENAPI
    version: str
    info: Dict = {}
    paths: Dict[str, Dict] = {}
    components: Optional[Dict] = None
    source_file: Optional[str] = None


class AnalysisResult(BaseModel):
    """API分析结果模型"""
    project_name: str
    source: str  # 'zip', 'github', 'local'
    source_info: Dict = {}
    apis: List[Union[RESTEndpoint, WebSocketAPI, GRPCService, GraphQLAPI, OpenAPISpec]] = []
    stats: Dict = {
        "REST": 0,
        "WebSocket": 0,
        "gRPC": 0,
        "GraphQL": 0,
        "OpenAPI": 0,
        "total": 0
    }
    errors: List[Dict] = []
    analyzed_at: datetime = Field(default_factory=datetime.now) 