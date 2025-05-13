#!/bin/bash
# Docker管理脚本 - 用于快速管理API检测器的Docker服务
# 使用requirements.txt管理Python依赖

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# 获取项目根目录路径
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 确保docker-compose.yml文件存在
if [ ! -f "docker-compose.yml" ]; then
    echo "错误: 在项目根目录未找到docker-compose.yml文件"
    exit 1
fi

# 显示帮助信息
show_help() {
    echo "API检测器 - Docker管理脚本"
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  start       启动服务"
    echo "  stop        停止服务"
    echo "  restart     重启服务"
    echo "  logs        查看日志"
    echo "  status      查看服务状态"
    echo "  build       重新构建镜像"
    echo "  clean       清理无用镜像和卷"
    echo "  help        显示帮助信息"
    echo ""
}

# 如果没有参数，显示帮助信息
if [ $# -eq 0 ]; then
    show_help
    exit 0
fi

# 处理命令
case "$1" in
    start)
        echo "启动API检测器服务..."
        docker-compose up -d
        echo "服务已启动，访问 http://localhost:8000"
        ;;
    stop)
        echo "停止API检测器服务..."
        docker-compose down
        echo "服务已停止"
        ;;
    restart)
        echo "重启API检测器服务..."
        docker-compose restart
        echo "服务已重启"
        ;;
    logs)
        echo "查看API检测器日志..."
        if [ "$2" == "-f" ]; then
            docker-compose logs -f
        else
            docker-compose logs
        fi
        ;;
    status)
        echo "API检测器服务状态:"
        docker-compose ps
        ;;
    build)
        echo "重新构建API检测器镜像..."
        docker-compose build --no-cache
        echo "构建完成"
        ;;
    clean)
        echo "清理无用的Docker资源..."
        docker system prune -f
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