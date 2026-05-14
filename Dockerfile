# IFA 上牌小助手 — Docker 镜像 (Milvus Lite 版)
# ============================================================
# 构建:  docker build -t ifa-lili-bot .
# 运行:  docker run -p 5000:5000 --env-file .env ifa-lili-bot
#
# 知识库: milvus.db (预构建的 Milvus Lite 向量数据库)
# 仅 25 chunks 时 milvus.db ~5MB（比 ChromaDB 的 ~50MB 更小）
# ============================================================

FROM python:3.12-slim

LABEL org.opencontainers.image.title="IFA 上牌小助手 (Lili Bot)"
LABEL org.opencontainers.image.description="企业微信 WorkTool 群消息 AI 助手，Milvus 向量检索 + Docker 一键部署"
LABEL org.opencontainers.image.version="1.1.0"

# ── 系统依赖 ──
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# ── 工作目录 ──
WORKDIR /app

# ── Python 依赖 ──
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── 应用代码 ──
COPY app.py .
COPY ifa_*.py ./
COPY wecom_sdk_long_connection.py ./

# ── 知识库（Milvus Lite） ──
# milvus.db 需预先构建（运行 rebuild_kb_v2.py）
COPY milvus.db ./

# ── ChromaDB 降级备选 ──
COPY chroma_db/ ./chroma_db/

# ── 端口 ──
EXPOSE 5000

# ── 环境变量默认值 ──
ENV FLASK_HOST=0.0.0.0
ENV FLASK_PORT=5000
ENV MILVUS_DB_PATH=/app/milvus.db
ENV MILVUS_COLLECTION=ifa_licensing_kb
ENV CHROMA_DB_PATH=/app/chroma_db
ENV CHROMA_COLLECTION=ifa_licensing_kb

# ── 健康检查 ──
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# ── 启动 ──
CMD ["python3", "app.py"]
