#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GitHub服务 - 处理GitHub仓库
"""

import os
import shutil
import zipfile
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

import git
import httpx

from app.core.config import settings
from app.utils.logger import logger


async def get_repo_default_branch(owner: str, repo: str) -> str:
    """
    获取GitHub仓库的默认分支
    
    Args:
        owner: 仓库所有者
        repo: 仓库名称
        
    Returns:
        默认分支名称
    """
    # 构建API URL
    api_url = f"{settings.GITHUB_API_URL}/repos/{owner}/{repo}"
    logger.debug(f"获取仓库默认分支: {api_url}")
    
    try:
        # 使用同步客户端请求GitHub API
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            response = client.get(api_url, headers={"Accept": "application/json"})
            response.raise_for_status()
            
            repo_info = response.json()
            default_branch = repo_info.get("default_branch", "main")
            logger.info(f"仓库默认分支: {default_branch}")
            return default_branch
            
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning(f"仓库不存在: {owner}/{repo}")
            raise ValueError(f"仓库不存在: {owner}/{repo}")
        else:
            logger.error(f"获取仓库信息失败: {str(e)}")
            raise ValueError(f"获取仓库信息失败: {str(e)}")
    except Exception as e:
        logger.error(f"获取仓库默认分支时出错: {str(e)}")
        # 如果无法获取默认分支，返回常见的默认分支名称
        return "main"


async def download_repository_zip(repo_url: str, branch: str = None) -> Path:
    """
    下载GitHub仓库的ZIP文件到临时目录
    
    Args:
        repo_url: GitHub仓库URL
        branch: 分支名，如果为None则使用默认分支
        
    Returns:
        解压后的目录路径
    """
    # 解析仓库所有者和名称
    parsed_url = urlparse(repo_url)
    path_parts = parsed_url.path.strip("/").split("/")
    
    if len(path_parts) < 2:
        raise ValueError(f"无效的GitHub仓库URL: {repo_url}")
    
    owner, repo_name = path_parts[:2]
    repo_name = repo_name.replace(".git", "")
    
    # 如果没有指定分支，获取默认分支
    if branch is None:
        try:
            branch = await get_repo_default_branch(owner, repo_name)
        except Exception as e:
            logger.warning(f"无法获取默认分支，使用'main': {str(e)}")
            branch = "main"
    
    # 创建临时目录
    temp_dir = Path(settings.TEMP_DIR)
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    zip_path = temp_dir / f"{repo_name}_{branch}.zip"
    extract_dir = temp_dir / f"github_{repo_name}_{branch}"
    
    # 如果目录已存在，先删除
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)
    
    # 构建下载URL，去除settings.GITHUB_BASE_URL最后的斜杠，因为路径中已包含斜杠
    github_base = settings.GITHUB_BASE_URL.rstrip('/')
    zip_url = f"{github_base}/{owner}/{repo_name}/archive/refs/heads/{branch}.zip"
    logger.info(f"正在下载仓库ZIP文件: {zip_url}")
    
    try:
        # 使用httpx同步客户端下载ZIP文件
        with httpx.Client(timeout=60.0, follow_redirects=True) as client:
            response = client.get(zip_url)
            response.raise_for_status()  # 如果请求失败则抛出异常
            
            # 将内容保存到临时ZIP文件
            zip_content = response.content
            with open(zip_path, 'wb') as f:
                f.write(zip_content)
                
            logger.info(f"下载完成，ZIP大小: {len(zip_content)} 字节")
        
        # 解压ZIP文件
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        logger.info(f"ZIP文件解压成功: {extract_dir}")
        
        # 找出解压后的主目录（通常是仓库名-分支名）
        contents = list(extract_dir.iterdir())
        if len(contents) == 1 and contents[0].is_dir():
            # 返回实际的仓库目录
            return contents[0]
        
        # 如果没有单一的主目录，返回解压目录
        return extract_dir
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            # 如果指定的分支不存在，尝试常见的其他分支
            common_branches = ["master", "main", "develop", "dev"]
            
            # 移除已尝试的分支
            if branch in common_branches:
                common_branches.remove(branch)
            
            # 尝试其他常见分支
            for alt_branch in common_branches:
                logger.info(f"分支 {branch} 不存在，尝试使用 {alt_branch} 分支")
                try:
                    return await download_repository_zip(repo_url, alt_branch)
                except Exception:
                    continue
                    
            # 如果所有常见分支都失败，则报错
            raise ValueError(f"无法找到仓库的有效分支: {owner}/{repo_name}")
        else:
            raise ValueError(f"下载仓库失败: {str(e)}")
    except Exception as e:
        logger.error(f"下载仓库ZIP文件失败: {str(e)}")
        raise ValueError(f"下载仓库失败: {str(e)}")
    finally:
        # 清理ZIP文件
        if zip_path.exists():
            zip_path.unlink()


async def clone_repository(repo_url: str, branch: str = "main") -> Path:
    """
    克隆GitHub仓库到临时目录
    
    Args:
        repo_url: GitHub仓库URL
        branch: 分支名
        
    Returns:
        克隆后的目录路径
    """
    # 创建临时目录
    repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
    clone_dir = Path(settings.TEMP_DIR) / f"github_{repo_name}_{branch}"
    
    # 如果目录已存在，先删除
    if clone_dir.exists():
        shutil.rmtree(clone_dir)
    
    # 创建目录
    clone_dir.mkdir(parents=True, exist_ok=True)
    
    # 构建克隆命令
    logger.info(f"正在克隆仓库: {repo_url} (分支: {branch})")
    
    if settings.GITHUB_TOKEN:
        # 如果设置了GitHub令牌，使用令牌进行认证
        auth_url = repo_url.replace('https://', f'https://oauth2:{settings.GITHUB_TOKEN}@')
        logger.debug("使用GitHub令牌进行认证")
    else:
        # 否则使用原始URL
        auth_url = repo_url
        
    try:
        # 克隆仓库
        git.Repo.clone_from(auth_url, clone_dir, branch=branch, depth=1)
        logger.info(f"仓库克隆成功: {clone_dir}")
        return clone_dir
    except git.exc.GitCommandError as e:
        logger.error(f"克隆仓库失败: {str(e)}")
        if "not found" in str(e).lower():
            # 可能是私有仓库或不存在
            raise ValueError(f"仓库未找到或需要访问权限。如果是私有仓库，请提供有效的GitHub令牌。")
        raise ValueError(f"克隆仓库失败: {str(e)}")


async def get_repo_info(repo_url: str) -> dict:
    """
    获取GitHub仓库信息
    
    Args:
        repo_url: GitHub仓库URL
        
    Returns:
        包含仓库信息的字典
    """
    try:
        # 解析仓库所有者和名称
        clean_url = repo_url.strip()
        
        # 移除URL前缀和后缀
        if settings.GITHUB_BASE_URL in clean_url:
            path = clean_url.split(settings.GITHUB_BASE_URL, 1)[1]
        else:
            path = clean_url
            
        path = path.rstrip("/").rstrip(".git")
        parts = path.split("/")
        
        if len(parts) < 2:
            raise ValueError(f"无效的GitHub仓库URL: {clean_url}")
        
        owner, repo = parts[:2]
        
        # 构建API URL
        api_url = f"{settings.GITHUB_API_URL}/repos/{owner}/{repo}"
        logger.debug(f"GitHub API URL: {api_url}")
        
        # 创建一个新的httpx客户端，禁用标头验证
        limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)
        timeout = httpx.Timeout(10.0, connect=5.0)
        
        async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
            # 设置最小化的请求头
            headers = {"Accept": "application/json"}
            
            # 如果设置了GitHub令牌，添加到请求头
            if settings.GITHUB_TOKEN:
                headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"
                
            # 发送请求
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()
            
            # 解析响应
            repo_info = response.json()
            
            # 提取感兴趣的信息
            result = {
                "name": repo_info.get("name", ""),
                "full_name": repo_info.get("full_name", ""),
                "description": repo_info.get("description", ""),
                "default_branch": repo_info.get("default_branch", "main"),
                "language": repo_info.get("language", ""),
                "stars": repo_info.get("stargazers_count", 0),
                "forks": repo_info.get("forks_count", 0),
                "open_issues": repo_info.get("open_issues_count", 0),
                "created_at": repo_info.get("created_at", ""),
                "updated_at": repo_info.get("updated_at", ""),
                "owner": {
                    "login": repo_info.get("owner", {}).get("login", ""),
                    "type": repo_info.get("owner", {}).get("type", "")
                }
            }
            
            return result
            
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning(f"仓库不存在: {repo_url}")
            raise ValueError(f"仓库不存在")
        else:
            logger.error(f"获取仓库信息失败: {str(e)}")
            raise ValueError(f"获取仓库信息失败: HTTP {e.response.status_code}")
    except UnicodeEncodeError as e:
        # 处理编码错误
        logger.error(f"处理GitHub API请求时出现编码错误: {str(e)}")
        raise ValueError(f"处理GitHub API请求时出现编码错误，请确保URL不包含非ASCII字符")
    except Exception as e:
        logger.error(f"GitHub API请求失败: {str(e)}")
        raise ValueError(f"无法连接到GitHub API: {str(e)}") 