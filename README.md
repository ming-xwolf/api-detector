# API检测器

一个自动化工具，用于检测代码库中的API定义和类型。

## 功能特性

- 支持多种API类型（REST、WebSocket、gRPC、GraphQL、OpenAPI）
- 从ZIP文件或GitHub仓库进行分析
- 生成详细的API文档和使用报告

## 环境设置

### 前提条件

- Python 3.10+
- Conda（推荐使用Anaconda或Miniconda）

### 依赖安装

1. 克隆仓库：
   ```bash
   git clone <repository-url>
   cd api-detector
   ```

2. 创建并激活conda环境：
   ```bash
   conda env create -f environment.yml
   conda activate api-detector
   ```

3. 安装额外依赖（如果需要使用.env配置）：
   ```bash
   pip install python-dotenv pydantic-settings
   ```

### 配置文件设置

项目使用`.env`文件进行配置。按照以下步骤设置：

1. 运行设置向导（推荐）：
   ```bash
   python scripts/setup_env.py
   ```
   或者更简单地，使用提供的shell脚本：
   ```bash
   ./setup.sh
   ```

2. 手动创建：复制下面的模板到项目根目录的`.env`文件中，并根据需要修改配置：

```ini
# API检测器 - 环境配置文件

# 应用设置
APP_NAME=API检测器
APP_VERSION=0.1.0
APP_ENV=development  # development | production | testing
DEBUG=true

# 服务器设置
HOST=0.0.0.0
PORT=8000
WORKERS=4
RELOAD=true  # 仅在开发环境使用

# GitHub相关设置
GITHUB_TOKEN=  # 如需更高API访问限制，请设置GitHub令牌

# 存储设置
UPLOAD_DIR=./data/uploads
TEMP_DIR=./data/temp
RESULTS_DIR=./data/results

# 安全设置
CORS_ORIGINS=*
API_KEY=  # 如需API认证，请设置此项

# 日志设置
LOG_LEVEL=INFO  # DEBUG | INFO | WARNING | ERROR | CRITICAL
LOG_FILE=./logs/api-detector.log
```

## 运行应用

1. 确保环境已激活：
   ```bash
   conda activate api-detector
   ```

2. 启动应用：
   ```bash
   python -m app.main
   ```

3. 在浏览器中访问：`http://localhost:8000`

## 开发指南

- 使用`black`和`isort`格式化代码
- 使用`pylint`和`mypy`进行代码质量检查
- 运行测试：`pytest tests/`

## 许可证

[MIT](LICENSE) 