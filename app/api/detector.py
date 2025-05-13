#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API检测器接口
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl
from typing import Optional

from app.models.api import AnalysisResult
from app.services.detector_service import detector_service
from app.services.file_service import cleanup_temp_files
from app.core.config import settings
from app.utils.logger import logger

router = APIRouter(prefix="/api", tags=["detector"])


class GitHubRepository(BaseModel):
    """GitHub仓库请求模型"""
    repo_url: HttpUrl
    branch: Optional[str] = None  # 可选参数，如果不提供则使用仓库默认分支


@router.post("/detect/upload", response_model=AnalysisResult)
async def detect_from_upload(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    """从上传的ZIP文件中检测API"""
    try:
        # 检查文件类型
        if not file.filename.endswith('.zip'):
            logger.warning(f"拒绝非ZIP文件: {file.filename}")
            raise HTTPException(status_code=400, detail="只接受ZIP文件")
        
        logger.info(f"接收到ZIP文件分析请求: {file.filename}")
        
        # 分析文件
        result = await detector_service.detect_from_upload(file)
        
        # 添加清理任务到后台
        if background_tasks:
            background_tasks.add_task(cleanup_temp_files)
        
        return result
    except Exception as e:
        logger.error(f"处理上传文件时出错: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理文件时出错: {str(e)}")


@router.post("/detect/github", response_model=AnalysisResult)
async def detect_from_github(repository: GitHubRepository, background_tasks: BackgroundTasks = None):
    """从GitHub仓库URL中检测API"""
    try:
        # 将HttpUrl对象转换为ASCII兼容的字符串
        repo_url_str = str(repository.repo_url)
        
        # 验证URL格式
        if not repo_url_str.startswith(settings.GITHUB_BASE_URL):
            raise ValueError(f"仅支持GitHub仓库URL ({settings.GITHUB_BASE_URL}...)")
            
        logger.info(f"接收到GitHub仓库分析请求: {repo_url_str}, 分支: {repository.branch}")
        
        # 分析仓库
        result = await detector_service.detect_from_github(repo_url_str, repository.branch)
        
        # 添加清理任务到后台
        if background_tasks:
            background_tasks.add_task(cleanup_temp_files)
        
        return result
    except ValueError as e:
        # 处理可预期的错误（如仓库不存在）
        logger.error(f"处理GitHub仓库时出错: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except UnicodeEncodeError as e:
        # 处理编码错误
        error_msg = "URL包含不支持的字符，请使用ASCII兼容的URL"
        logger.error(f"处理GitHub仓库时出现编码错误: {str(e)}")
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        logger.error(f"处理GitHub仓库时出错: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理GitHub仓库时出错: {str(e)}")


@router.get("/types")
def api_types():
    """获取支持的API类型"""
    return {
        "types": [
            {"id": "REST", "name": "REST API", "description": "RESTful API，基于HTTP请求"},
            {"id": "WebSocket", "name": "WebSocket API", "description": "基于WebSocket的实时通信API"},
            {"id": "gRPC", "name": "gRPC API", "description": "基于gRPC的高性能API"},
            {"id": "GraphQL", "name": "GraphQL API", "description": "基于GraphQL的查询API"},
            {"id": "OpenAPI", "name": "OpenAPI/Swagger", "description": "OpenAPI/Swagger规范文档"}
        ]
    } 