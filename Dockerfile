# IFA 上牌小助手 — Docker 镜像
# ============================================================
# 构建:  docker build -t ifa-lili-bot .
# 运行:  docker run -p 5000:5000 --env-file .env ifa-lili-bot
#
# 需要预构建 ChromaDB（chroma_db/ 目录）
# 如果 chroma_db/ 不存在，构建会跳过（运行时 RAG 不可用）
# ============================================================

FROM python:3.12-slim

LABEL org.opencontainers.image.title="IFA 上牌小助手 (Lili Bot)"
LABEL org.opencontainers.image.description="企业微信 WorkTool 群消息 AI 助手，支持上牌流程引导和知识库问答"
LABEL org.opencontainers.image.version="1.0.0"

# ── 系统依赖 ──
# chromadb 需要 libsqlite3, sentence-transformers 需要 libgomp1
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsqlite3-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# ── 工作目录 ──
WORKDIR /app

# ── Python 依赖 ──
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── 应用代码 ──
COPY app.py .
# 复制其他功能脚本（可选，供调试和扩展使用）
COPY ifa_*.py ./
COPY wecom_sdk_long_connection.py ./

# ── 知识库（如果存在） ──
# chroma_db 需要预先构建（运行 rebuild_kb_v2.py 或使用已有的）
COPY chroma_db/ ./chroma_db/

# ── 端口 ──
EXPOSE 5000

# ── 环境变量默认值 ──
ENV FLASK_HOST=0.0.0.0
ENV FLASK_PORT=5000
ENV CHROMA_DB_PATH=/app/chroma_db
ENV CHROMA_COLLECTION=ifa_licensing_kb

# ── 健康检查 ──
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# ── 启动 ──
# 生产环境推荐: CMD ["gunicorn", "app:app", "-b", "0.0.0.0:5000", "-w", "2"]
# 开发/测试用 Flask 内置服务器:
CMD ["python3", "app.py"]
