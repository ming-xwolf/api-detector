# 使用Alpine Linux作为基础镜像
FROM python:3.10-alpine

# 设置工作目录
WORKDIR /app

# 设置Python环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# 安装系统依赖
RUN apk add --no-cache git gcc musl-dev

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 确保目录存在
RUN mkdir -p data/uploads data/temp data/results logs

# 暴露应用端口
EXPOSE 8000

# 设置启动命令
CMD ["python", "-m", "app.main"] 