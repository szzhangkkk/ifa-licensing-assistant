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
LABEL org.opencontainers.image.version="1.3.0"

# ── 系统依赖 ──
# 使用阿里云镜像加速（国内下载 Debian 包更快）
RUN sed -i 's|http://deb.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's|http://security.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── 工作目录 ──
WORKDIR /app

# ── Python 依赖 ──
# 先装 CPU 版 torch（必须用 --index-url 指向 pytorch CPU 源，
# 避免清华源拉到 CUDA 版 ~2GB）
RUN pip install --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cpu \
    --trusted-host download.pytorch.org \
    torch

# 其余依赖走清华源（国内更快）
ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple/

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Embedding 模型（宿主机预下载 → COPY 进镜像，彻底离线）──
# 模型由 deploy.sh 在构建前自动复制到 hf_model_cache/
ENV HF_HUB_OFFLINE=1
COPY hf_model_cache/ /root/.cache/huggingface/hub/

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

# ── 健康检查 ──
# start-period=60s：模型加载 + Milvus 初始化首次可能较慢
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -sf http://localhost:5000/health > /dev/null 2>&1 || exit 1

# ── 启动 ──
CMD ["python3", "app.py"]
