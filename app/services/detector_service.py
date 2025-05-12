#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API检测服务 - 检测代码库中的API
"""

from pathlib import Path
from typing import Dict
from urllib.parse import urlparse

from fastapi import UploadFile

from app.models.api import AnalysisResult
from app.services.detectors.codebase_analyzer import CodebaseAnalyzer
from app.services.file_service import cleanup_temp_files, extract_zip, save_upload_file
from app.services.github_service import download_repository_zip
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
            result = await self.analyzer.analyze(
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


# 创建服务实例
detector_service = APIDetectorService() 