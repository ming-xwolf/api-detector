#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API检测服务 - 检测代码库中的API
"""

import os
from pathlib import Path
from typing import Dict
from urllib.parse import urlparse

from fastapi import UploadFile

from app.models.api import AnalysisResult
from app.services.detectors.codebase_analyzer import CodebaseAnalyzer
from app.services.file_service import cleanup_temp_files, extract_zip, save_upload_file
from app.services.git_service import clone_repository, get_repo_info, download_repository_zip
from app.utils.logger import logger


class APIDetectorService:
    """API检测服务"""
    
    def __init__(self):
        """初始化检测服务"""
        self.analyzer = CodebaseAnalyzer()
    
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
            result = await self.analyzer.analyze(extract_dir, f"zip:{file.filename}")
            
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
    
    async def detect_from_git(self, repo_url: str, branch: str = None) -> AnalysisResult:
        """
        从Git仓库中检测API（先尝试克隆方式，如果失败则尝试ZIP方式）
        
        Args:
            repo_url: Git仓库URL
            branch: 分支名，如果为None则使用仓库默认分支
            
        Returns:
            API分析结果
        """
        # 确保repo_url是字符串类型
        repo_url_str = str(repo_url)
        
        try:
            # 首先尝试通过克隆方式检测
            logger.info(f"尝试通过克隆方式检测仓库: {repo_url_str}")
            result = await self.detect_from_git_clone(repo_url_str, branch)
            return result
        except Exception as e:
            # 克隆方式失败，记录错误并尝试ZIP方式
            logger.warning(f"通过克隆方式检测失败，将尝试ZIP方式: {str(e)}")
            
            try:
                # 尝试通过ZIP方式检测
                logger.info(f"尝试通过ZIP方式检测仓库: {repo_url_str}")
                result = await self.detect_from_git_zip(repo_url_str, branch)
                return result
            except Exception as zip_error:
                # 如果ZIP方式也失败，记录错误并返回原始错误信息
                logger.error(f"通过ZIP方式检测也失败: {str(zip_error)}")
                
                # 创建包含错误信息的结果
                parsed_url = urlparse(repo_url_str)
                path_parts = parsed_url.path.strip("/").split("/")
                repo_name = path_parts[-1].replace('.git', '') if path_parts else "unknown"
                
                return AnalysisResult(
                    project_name=repo_name,
                    source="git",
                    source_info={"repo_url": repo_url_str},
                    errors=[
                        {"message": f"克隆方式失败: {str(e)}"},
                        {"message": f"ZIP方式失败: {str(zip_error)}"}
                    ]
                )
    
    async def detect_from_git_clone(self, repo_url: str, branch: str = None) -> AnalysisResult:
        """
        从Git仓库中通过克隆方式检测API
        
        Args:
            repo_url: Git仓库URL
            branch: 分支名，如果为None则使用仓库默认分支
            
        Returns:
            API分析结果
        """
        # 确保repo_url是字符串类型
        repo_url_str = str(repo_url)
        repo_dir = None
        
        try:
            # 获取仓库信息
            repo_info = await get_repo_info(repo_url_str)
            repo_type = repo_info.get("type", "git")
            repo_name = repo_info.get("repo_name", "unknown")
            
            # 构建项目名称
            owner = repo_info.get("owner")
            project_name = f"{owner}/{repo_name}" if owner else repo_name
            
            # 下载仓库
            branch_info = f", 分支: {branch}" if branch else " (使用默认分支)"
            logger.info(f"开始下载{repo_type}仓库: {project_name}{branch_info}")
            
            # 克隆仓库
            repo_dir = await clone_repository(repo_url_str, branch)
            logger.info(f"成功克隆仓库: {project_name}")
            
            # 分析代码库
            result = await self.analyzer.analyze(
                repo_dir, 
                repo_type,
                project_name
            )
            
            # 添加仓库信息到结果中
            result.source_info = repo_info
            
            # 添加分支信息
            result.source_info["branch"] = branch or "默认分支"
            result.source_info["method"] = "clone"
            
            # 清理临时文件
            cleanup_temp_files(repo_dir)
            
            return result
            
        except Exception as e:
            logger.error(f"从Git仓库克隆检测API时出错: {str(e)}", exc_info=True)
            # 清理临时文件
            if repo_dir and Path(repo_dir).exists():
                cleanup_temp_files(repo_dir)
                
            # 抛出异常，让上层方法处理
            raise
            
    async def detect_from_git_zip(self, repo_url: str, branch: str = None) -> AnalysisResult:
        """
        从Git仓库下载ZIP文件并检测API
        
        Args:
            repo_url: Git仓库URL
            branch: 分支名，如果为None则使用仓库默认分支
            
        Returns:
            API分析结果
        """
        # 确保repo_url是字符串类型
        repo_url_str = str(repo_url)
        zip_path = None
        extract_dir = None
        
        try:
            # 获取仓库信息
            repo_info = await get_repo_info(repo_url_str)
            repo_type = repo_info.get("type", "git")
            repo_name = repo_info.get("repo_name", "unknown")
            
            # 构建项目名称
            owner = repo_info.get("owner")
            project_name = f"{owner}/{repo_name}" if owner else repo_name
            
            # 下载仓库ZIP文件
            branch_info = f", 分支: {branch}" if branch else " (使用默认分支)"
            logger.info(f"开始下载{repo_type}仓库ZIP文件: {project_name}{branch_info}")
            
            # 下载ZIP文件
            zip_path = await download_repository_zip(repo_url_str, branch)
            logger.info(f"成功下载仓库ZIP文件: {project_name}")
            
            # 解压ZIP文件
            extract_dir = await extract_zip(zip_path)
            logger.info(f"成功解压仓库ZIP文件: {project_name}")
            
            # 分析代码库
            result = await self.analyzer.analyze(
                extract_dir, 
                repo_type,
                project_name
            )
            
            # 添加仓库信息到结果中
            result.source_info = repo_info
            
            # 添加分支信息
            result.source_info["branch"] = branch or "默认分支"
            result.source_info["method"] = "zip"
            
            # 清理临时文件
            if zip_path and Path(zip_path).exists():
                cleanup_temp_files(zip_path)
            if extract_dir and Path(extract_dir).exists():
                cleanup_temp_files(extract_dir)
            
            return result
            
        except Exception as e:
            logger.error(f"从Git仓库ZIP文件检测API时出错: {str(e)}", exc_info=True)
            # 清理临时文件
            if zip_path and Path(zip_path).exists():
                cleanup_temp_files(zip_path)
            if extract_dir and Path(extract_dir).exists():
                cleanup_temp_files(extract_dir)
                
            # 抛出异常，让上层方法处理
            raise


# 创建服务单例
detector_service = APIDetectorService() 