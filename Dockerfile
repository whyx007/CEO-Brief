FROM python:3.10-slim

# 匹配源代码路径层级，避免 parents[] 越界
WORKDIR /home/ai/code/ceo-brief-deploy

# 复制项目代码（不含 company-summary）
COPY . .

# competitive_analysis 从 PLATFORM_ROOT 加载 .env，确保同级目录也有
RUN mkdir -p /home/ai/code && cp -f /home/ai/code/ceo-brief-deploy/.env /home/ai/code/.env

# 创建 company-summary 挂载点目录
RUN mkdir -p /data/company-summary

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir openpyxl

# 暴露端口
EXPOSE 8000

# 启动服务
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
