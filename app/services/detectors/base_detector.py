#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API检测器基类 - 提供基础功能
"""

from pathlib import Path


class BaseDetector:
    """API检测器基类"""
    
    def __init__(self):
        """初始化基础检测器"""
        pass
        
    def _get_relative_path(self, file_path: Path, codebase_path: Path) -> str:
        """获取相对路径"""
        return str(file_path.relative_to(codebase_path))
        
    def _get_line_number(self, content: str, match_start: int) -> int:
        """获取匹配位置的行号"""
        return content[:match_start].count('\n') + 1 