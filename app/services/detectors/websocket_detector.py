#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WebSocket API检测器 - 检测WebSocket API
"""

import re
import uuid
from pathlib import Path
from typing import List

from app.models.api import WebSocketAPI
from app.services.detectors.base_detector import BaseDetector


class WebSocketDetector(BaseDetector):
    """WebSocket API检测器"""
    
    def __init__(self):
        """初始化WebSocket API检测器"""
        super().__init__()
        self.patterns = {
            'websocket_route': re.compile(r'@(app|router)\.websocket\s*\(\s*[\'"](?P<path>[^\'"]+)[\'"]'),
            'socketio': re.compile(r'@?socketio\.(on|event)\s*\(\s*[\'"](?P<event>[^\'"]+)[\'"]'),
        }
        
    def detect(self, content: str, file_path: Path, codebase_path: Path) -> List[WebSocketAPI]:
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
                source_file=self._get_relative_path(file_path, codebase_path),
                source_line=self._get_line_number(content, match.start())
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
                source_file=self._get_relative_path(file_path, codebase_path),
                source_line=1  # 默认第一行
            )
            
            apis.append(api)
            
        return apis 