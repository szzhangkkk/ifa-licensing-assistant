# IFA 上牌小助手 — Docker 镜像 (Milvus Lite 版)
# ============================================================
# 构建:  docker build -t ifa-lili-bot .
# 运行:  docker run -p 5000:5000 --env-file .env ifa-lili-bot
#
# 知识库: milvus.db（预构建的 Milvus Lite 向量数据库）
# 嵌入模型: paraphrase-multilingual-MiniLM-L12-v2（预下载到镜像）
# ============================================================

FROM python:3.12-slim

LABEL org.opencontainers.image.title="IFA 上牌小助手 (Lili Bot)"
LABEL org.opencontainers.image.description="企业微信 WorkTool 群消息 AI 助手，Milvus 向量检索 + Docker 一键部署"
LABEL org.opencontainers.image.version="1.2.0"

# ── 系统依赖 ──
# 使用阿里云镜像加速（国内下载 Debian 包更快）
RUN sed -i 's|http://deb.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's|http://security.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# ── 工作目录 ──
WORKDIR /app

# ── Python 依赖（先 pip install，利用 Docker 层缓存）──
# 使用清华 PyPI 镜像（国内下载更快）
ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple/

# 先装 CPU 版 torch（避免拉取 ~2GB CUDA 全家桶，纯 CPU 部署不需要）
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── 预下载 embedding 模型到镜像（避免启动时下载 470MB 导致超时）──
# 使用 HF 镜像站（国内下载更快）
ENV HF_ENDPOINT=https://hf-mirror.com

RUN python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

# ── 应用代码 ──
COPY app.py .

# ── 知识库（Milvus Lite — 必须先运行 rebuild_kb_v2.py 生成）──
COPY milvus.db ./

# ── ChromaDB 降级备选（可选，Milvus 不可用时自动切换）──
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
ENV HF_HUB_OFFLINE=1

# ── 健康检查 ──
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# ── 启动 ──
CMD ["python3", "app.py"]
