@echo off
REM API检测器 - 本地环境设置和运行脚本 (Windows版本)
REM 使用conda环境和requirements.txt管理依赖

IF "%1"=="" (
    GOTO :help
)

REM 确保我们在项目根目录
IF NOT EXIST "requirements.txt" (
    echo 错误: 请在项目根目录运行此脚本
    exit /b 1
)

REM 确保conda命令可用
WHERE conda >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    echo 错误: 未找到conda命令，请先安装Anaconda或Miniconda
    exit /b 1
)

IF "%1"=="setup" (
    echo 创建conda环境 'api-detector'...
    call conda create -y -n api-detector python=3.10
    call conda activate api-detector
    echo 安装依赖...
    call pip install --upgrade pip
    call pip install -r requirements.txt
    echo 创建必要的目录...
    if not exist data\uploads mkdir data\uploads
    if not exist data\temp mkdir data\temp
    if not exist data\results mkdir data\results
    if not exist logs mkdir logs
    echo 设置完成。使用 'setup.bat run' 运行应用
    GOTO :end
)

REM 激活conda环境
FOR /F "tokens=*" %%i IN ('conda env list ^| findstr /C:"api-detector"') DO SET ENV_FOUND=1
IF NOT DEFINED ENV_FOUND (
    echo 错误: conda环境不存在，请先运行 'setup.bat setup'
    exit /b 1
)
call conda activate api-detector

IF "%1"=="run" (
    echo 启动API检测器服务...
    python -m app.main
    GOTO :end
)

IF "%1"=="test" (
    echo 运行测试...
    pytest tests/
    GOTO :end
)

IF "%1"=="format" (
    echo 格式化代码...
    black app/ tests/
    isort app/ tests/
    echo 格式化完成
    GOTO :end
)

IF "%1"=="lint" (
    echo 运行代码检查...
    pylint app/ tests/
    mypy app/ tests/
    echo 代码检查完成
    GOTO :end
)

IF "%1"=="clean" (
    echo 清理Python缓存文件...
    for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
    del /s /q *.pyc *.pyo *.pyd
    echo 清理完成
    GOTO :end
)

IF "%1"=="help" (
    GOTO :help
) ELSE (
    echo 错误: 未知命令 '%1'
    GOTO :help
)

:help
echo API检测器 - 本地环境设置和运行脚本 (Windows版本)
echo 用法: setup.bat [命令]
echo.
echo 命令:
echo   setup       设置conda环境并安装依赖
echo   run         运行应用
echo   test        运行测试
echo   format      格式化代码 (black和isort)
echo   lint        运行代码检查 (pylint和mypy)
echo   clean       清理Python缓存文件
echo   help        显示帮助信息
echo.
GOTO :end

:end 