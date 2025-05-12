# API检测器

一个自动化工具，用于检测代码库中的API定义和类型。

## 功能特性

- 支持多种API类型检测：
  - REST API（FastAPI、Flask、Express、Spring等框架）
  - WebSocket API
  - gRPC服务
  - GraphQL API
  - OpenAPI/Swagger规范
- 多种代码库分析方式：
  - 上传ZIP文件分析
  - 直接从GitHub仓库URL分析
- 详细的API识别与分类
- 自动生成API使用报告和统计信息
- 异步处理大型代码库
- 后台任务自动清理临时文件

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

手动创建：复制下面的模板到项目根目录的`.env`文件中，并根据需要修改配置：

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
TEMP_RETENTION_DAYS=1  # 临时文件保留天数

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

## API使用指南

### 1. 检测上传的ZIP文件中的API

**端点**: `POST /api/detect/upload`

**请求**:
- 使用表单数据上传ZIP文件

**响应**:
```json
{
  "project_name": "项目名称",
  "source": "zip",
  "source_info": { "filename": "上传的文件名" },
  "apis": [...],  // 检测到的API列表
  "stats": {
    "REST": 5,
    "WebSocket": 2,
    "gRPC": 1,
    "GraphQL": 0,
    "OpenAPI": 1,
    "total": 9
  },
  "errors": [],
  "analyzed_at": "2023-05-01T12:34:56"
}
```

### 2. 从GitHub仓库检测API

**端点**: `POST /api/detect/github`

**请求**:
```json
{
  "repo_url": "https://github.com/用户名/仓库名",
  "branch": "main"  // 可选，默认使用仓库默认分支
}
```

**响应**: 与上传ZIP文件相同格式

### 3. 获取支持的API类型

**端点**: `GET /api/types`

**响应**:
```json
{
  "types": [
    {"id": "REST", "name": "REST API", "description": "RESTful API，基于HTTP请求"},
    {"id": "WebSocket", "name": "WebSocket API", "description": "基于WebSocket的实时通信API"},
    {"id": "gRPC", "name": "gRPC API", "description": "基于gRPC的高性能API"},
    {"id": "GraphQL", "name": "GraphQL API", "description": "基于GraphQL的查询API"},
    {"id": "OpenAPI", "name": "OpenAPI/Swagger", "description": "OpenAPI/Swagger规范文档"}
  ]
}
```

## 开发指南

### 代码风格

- 遵循PEP 8编码规范
- 使用4个空格进行缩进
- 每行最大长度为88个字符（Black格式化标准）
- 使用类型注解提高代码可读性
- 使用docstring为函数和类添加文档

### 命名约定

- **变量和函数**: 使用小写下划线命名法 (snake_case)
- **类名**: 使用大驼峰命名法 (PascalCase)
- **常量**: 全部大写，下划线分隔 (UPPER_CASE)
- **私有成员**: 使用单下划线前缀 (_private_var)

### 工具推荐

- 使用`black`和`isort`格式化代码
- 使用`pylint`和`mypy`进行代码质量检查
- 运行测试：`pytest tests/`

## 许可证

[MIT](LICENSE) 