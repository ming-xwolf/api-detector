#!/bin/bash
# API检测器 - 本地环境设置和运行脚本
# 使用conda环境和requirements.txt管理依赖

# 显示帮助信息
show_help() {
    echo "API检测器 - 本地环境设置和运行脚本"
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  setup       设置conda环境并安装依赖"
    echo "  run         运行应用"
    echo "  test        运行测试"
    echo "  format      格式化代码 (black和isort)"
    echo "  lint        运行代码检查 (pylint和mypy)"
    echo "  clean       清理Python缓存文件"
    echo "  help        显示帮助信息"
    echo ""
}

# 如果没有参数，显示帮助信息
if [ $# -eq 0 ]; then
    show_help
    exit 0
fi

# 确保我们在项目根目录
if [ ! -f "requirements.txt" ]; then
    echo "错误: 请在项目根目录运行此脚本"
    exit 1
fi

# 确保conda命令可用
if ! command -v conda &> /dev/null; then
    echo "错误: 未找到conda命令，请先安装Anaconda或Miniconda"
    exit 1
fi

# 激活conda环境
activate_conda_env() {
    if conda info --envs | grep -q "^api-detector"; then
        eval "$(conda shell.bash hook)"
        conda activate api-detector
    else
        echo "错误: conda环境不存在，请先运行 '$0 setup'"
        exit 1
    fi
}

# 处理命令
case "$1" in
    setup)
        echo "创建conda环境 'api-detector'..."
        conda create -y -n api-detector python=3.10
        eval "$(conda shell.bash hook)"
        conda activate api-detector
        echo "安装依赖..."
        pip install --upgrade pip
        pip install -r requirements.txt
        echo "创建必要的目录..."
        mkdir -p data/uploads data/temp data/results logs
        echo "设置完成。使用 '$0 run' 运行应用"
        ;;
    run)
        activate_conda_env
        echo "启动API检测器服务..."
        python -m app.main
        ;;
    test)
        activate_conda_env
        echo "运行测试..."
        pytest tests/
        ;;
    format)
        activate_conda_env
        echo "格式化代码..."
        black app/ tests/
        isort app/ tests/
        echo "格式化完成"
        ;;
    lint)
        activate_conda_env
        echo "运行代码检查..."
        pylint app/ tests/
        mypy app/ tests/
        echo "代码检查完成"
        ;;
    clean)
        echo "清理Python缓存文件..."
        find . -type d -name "__pycache__" -exec rm -rf {} +
        find . -type f -name "*.pyc" -delete
        find . -type f -name "*.pyo" -delete
        find . -type f -name "*.pyd" -delete
        find . -type d -name "*.egg-info" -exec rm -rf {} +
        find . -type d -name "*.egg" -exec rm -rf {} +
        find . -type d -name ".pytest_cache" -exec rm -rf {} +
        find . -type d -name ".coverage" -exec rm -rf {} +
        find . -type d -name "htmlcov" -exec rm -rf {} +
        echo "清理完成"
        ;;
    help)
        show_help
        ;;
    *)
        echo "错误: 未知命令 '$1'"
        show_help
        exit 1
        ;;
esac

exit 0 