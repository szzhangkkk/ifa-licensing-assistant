#!/usr/bin/env bash
# ============================================================
# IFA 上牌小助手 (Lili Bot) — 一键部署脚本
# ============================================================
# 用法:
#   ./deploy.sh              # 交互式部署（推荐）
#   ./deploy.sh quick        # 快速部署（跳过确认）
#   ./deploy.sh stop         # 停止服务
#   ./deploy.sh logs         # 查看日志
#   ./deploy.sh status       # 查看状态
#   ./deploy.sh no-ngrok     # 不使用 ngrok 部署
#
# 前置条件:
#   - Docker 已安装 (https://docs.docker.com/get-docker/)
#   - Docker Compose 已安装
#   - 已从 WorkTool 控制台获取 ROBOT_ID
#   - (可选) ngrok 账号 + authtoken
# ============================================================

set -e

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ────────────────────────────────────────
# 工具函数
# ────────────────────────────────────────

print_banner() {
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║     IFA 上牌小助手 (Lili Bot) — 一键部署        ║${NC}"
    echo -e "${BLUE}║                v1.3.0                            ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════╝${NC}"
    echo ""
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}[错误] 未检测到 Docker，请先安装:${NC}"
        echo "  https://docs.docker.com/get-docker/"
        exit 1
    fi

    if ! docker compose version &> /dev/null; then
        echo -e "${RED}[错误] 未检测到 Docker Compose，请安装 Docker Desktop 或 docker-compose-plugin${NC}"
        exit 1
    fi

    # 检查 curl（deploy.sh 健康检查依赖它）
    if ! command -v curl &> /dev/null; then
        echo -e "${RED}[错误] 未检测到 curl，请先安装:${NC}"
        echo "  sudo apt install curl        # Debian/Ubuntu"
        echo "  sudo yum install curl        # CentOS/RHEL"
        exit 1
    fi

    # 检查 daemon 是否可达（compose version 不需要 daemon，但 build 需要）
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}[错误] Docker daemon 未运行或当前用户无权限${NC}"
        echo ""
        echo "  请检查:"
        echo "  1. Docker daemon 是否在运行: sudo systemctl start docker"
        echo "  2. 当前用户是否在 docker 组: groups"
        echo "  3. 如果不在，执行: sudo usermod -aG docker \$USER && newgrp docker"
        exit 1
    fi

    # 检查 Docker 镜像加速（国内服务器建议配置）
    if ! docker info 2>/dev/null | grep -q 'Registry Mirrors'; then
        echo -e "${YELLOW}[!] 未检测到 Docker 镜像加速，docker pull 可能很慢${NC}"
        echo ""
        echo "  建议配置 Docker 镜像加速（任选其一）:"
        echo ""
        echo "  方案 A — 阿里云镜像加速（需注册获取专属地址）:"
        echo "    https://cr.console.aliyun.com → 镜像工具 → 镜像加速器"
        echo ""
        echo "  方案 B — 通用镜像:"
        echo "    sudo mkdir -p /etc/docker"
        echo "    sudo tee /etc/docker/daemon.json <<'EOF'"
        echo '    {'
        echo '      "registry-mirrors": ['
        echo '        "https://docker.1ms.run",'
        echo '        "https://docker.xuanyuan.me"'
        echo '      ]'
        echo '    }'
        echo '    EOF'
        echo "    sudo systemctl restart docker"
        echo ""
        read -p "  跳过继续? [Y/n] " -r
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            exit 0
        fi
    fi

    echo -e "${GREEN}[✓] Docker 环境已就绪${NC}"
}

check_env() {
    if [ ! -f ".env" ]; then
        echo -e "${YELLOW}[!] 未找到 .env 文件${NC}"
        echo ""

        if [ -f ".env.example" ]; then
            echo "  正在从 .env.example 创建 .env..."
            cp .env.example .env
        else
            echo -e "${RED}[错误] .env.example 也不存在${NC}"
            exit 1
        fi

        echo ""
        echo -e "${YELLOW}  ⚠️  重要：请编辑 .env 文件，填入你的 Robot ID${NC}"
        echo ""
        echo "  需要填写的关键配置:"
        echo "    WORKTOOL_ROBOT_ID=你的robotId"
        echo "    (可选) NGROK_AUTH_TOKEN=你的ngrok authtoken"
        echo ""
        echo "  获取 robotId: 登录 https://console.worktool.ymdyes.cn → 机器人配置"
        echo "  获取 ngrok token: 注册 https://ngrok.com → Your Authtoken"
        echo ""

        read -p "  是否现在编辑 .env 文件? [Y/n] " -r
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            ${EDITOR:-nano} .env
        fi
    fi

    # 检查必需配置
    source .env 2>/dev/null || true
    if [ -z "$WORKTOOL_ROBOT_ID" ] || [ "$WORKTOOL_ROBOT_ID" = "your_robot_id_here" ]; then
        echo ""
        echo -e "${RED}[错误] WORKTOOL_ROBOT_ID 未配置!${NC}"
        echo "  请编辑 .env 文件，设置正确的 robotId"
        echo "  获取方式: WorkTool 控制台 → 机器人配置 → 复制 robotId"
        exit 1
    fi

    echo -e "${GREEN}[✓] 配置文件已就绪${NC}"
}

check_vectordb() {
    # Docker build 依赖 milvus.db，必须存在
    if [ ! -f "milvus.db" ]; then
        echo ""
        echo -e "${RED}[错误] milvus.db 未找到，Docker 构建会失败（Dockerfile 有 COPY milvus.db）${NC}"
        echo ""
        echo "  请先构建知识库:"
        echo "    python3 rebuild_kb_v2.py"
        echo ""
        exit 1
    fi
    echo -e "${GREEN}[✓] 知识库已就绪 (Milvus Lite: $(du -h milvus.db | cut -f1))${NC}"

    if [ -d "chroma_db" ] && [ -f "chroma_db/chroma.sqlite3" ]; then
        echo -e "${GREEN}[✓] ChromaDB 降级备选已就绪${NC}"
    fi
}

check_model_cache() {
    # 确保 HF 模型缓存存在于项目目录（Docker build 需要 COPY hf_model_cache/）
    # 策略：hf_model_cache/ 已有 → 跳过
    #       宿主机 HF 缓存有 → 复制（秒级）
    #       都没有 → 宿主机自动下载（首次约 2-5 分钟，仅一次）
    local MODEL_NAME="paraphrase-multilingual-MiniLM-L12-v2"
    local HF_CACHE_SRC="$HOME/.cache/huggingface/hub/models--sentence-transformers--${MODEL_NAME}"
    local HF_CACHE_DST="./hf_model_cache/models--sentence-transformers--${MODEL_NAME}"

    # 1) 项目目录已有 → 直接返回
    if [ -d "$HF_CACHE_DST" ] && compgen -G "$HF_CACHE_DST/snapshots/*/model.safetensors" > /dev/null 2>&1; then
        echo -e "${GREEN}[✓] HF 模型缓存已就绪 (${HF_CACHE_DST})${NC}"
        return 0
    fi

    # 2) 宿主机 HF 缓存有 → 快速复制
    if [ -d "$HF_CACHE_SRC" ] && compgen -G "$HF_CACHE_SRC/snapshots/*/model.safetensors" > /dev/null 2>&1; then
        echo ""
        echo -e "${YELLOW}[!] 正在从宿主机 HF 缓存复制模型 (约 458MB)...${NC}"
        mkdir -p "$(dirname "$HF_CACHE_DST")"
        cp -rL "$HF_CACHE_SRC" "$HF_CACHE_DST"
        rm -rf "$HF_CACHE_DST/blobs"   # snapshots 已是实体文件，blobs 冗余
        echo -e "${GREEN}[✓] 模型缓存已复制 ($(du -sh "$HF_CACHE_DST" | cut -f1))${NC}"
        return 0
    fi

    # 3) 都没有 → 宿主机下载（用 huggingface-hub，比 sentence-transformers 轻量得多）
    echo ""
    echo -e "${YELLOW}[!] 首次部署：正在下载 embedding 模型 (约 470MB, 可能需要 2-5 分钟)...${NC}"
    echo "  模型: sentence-transformers/${MODEL_NAME}"
    echo "  镜像: https://hf-mirror.com (HuggingFace 国内镜像)"
    echo ""

    # 仅需 huggingface-hub（~5MB），不需要 sentence-transformers + torch（~2GB）
    if ! python3 -c "import huggingface_hub" 2>/dev/null; then
        echo -e "${YELLOW}[!] 正在安装 huggingface-hub（轻量依赖，约 5MB）...${NC}"
        if python3 -m pip install --quiet -i https://pypi.tuna.tsinghua.edu.cn/simple huggingface-hub 2>/dev/null; then
            :
        elif command -v pip3 &>/dev/null && pip3 install --quiet -i https://pypi.tuna.tsinghua.edu.cn/simple huggingface-hub 2>/dev/null; then
            :
        elif command -v pip &>/dev/null && pip install --quiet -i https://pypi.tuna.tsinghua.edu.cn/simple huggingface-hub 2>/dev/null; then
            :
        else
            echo ""
            echo -e "${RED}[错误] 无法安装 huggingface-hub（pip 不可用）${NC}"
            echo ""
            echo "  请手动安装 pip 后再试:"
            echo "    sudo apt install python3-pip        # Debian/Ubuntu"
            echo "    sudo yum install python3-pip        # CentOS/RHEL"
            echo ""
            exit 1
        fi
    fi

    # 用 huggingface-hub 下载模型文件到默认 HF 缓存（纯文件下载，不加载到内存）
    # 加 3 次重试，间隔 5 秒（hf-mirror.com 网络抖动时自动恢复）
    local download_ok=0
    for attempt in 1 2 3; do
        echo "  第 ${attempt}/3 次尝试下载..."
        if HF_ENDPOINT=https://hf-mirror.com python3 -c "
from huggingface_hub import snapshot_download
snapshot_download(repo_id='sentence-transformers/${MODEL_NAME}')
" 2>&1; then
            download_ok=1
            break
        fi
        if [ "$attempt" -lt 3 ]; then
            echo -e "${YELLOW}  下载失败，5 秒后重试...${NC}"
            sleep 5
        fi
    done
    if [ "$download_ok" -eq 1 ]; then
        echo ""
        echo -e "${GREEN}[✓] 模型下载完成${NC}"

        # 复制到项目目录
        echo -e "${YELLOW}[!] 正在复制到项目目录...${NC}"
        mkdir -p "$(dirname "$HF_CACHE_DST")"
        cp -rL "$HF_CACHE_SRC" "$HF_CACHE_DST"
        rm -rf "$HF_CACHE_DST/blobs"   # snapshots 已是实体文件，blobs 冗余
        echo -e "${GREEN}[✓] 模型缓存已就绪 ($(du -sh "$HF_CACHE_DST" | cut -f1))${NC}"
    else
        echo ""
        echo -e "${RED}[错误] 模型下载失败（已重试 3 次）${NC}"
        echo ""
        echo "  可能的原因:"
        echo "  1. 网络无法访问 hf-mirror.com"
        echo "  2. 磁盘空间不足（需要约 1GB）"
        echo ""
        echo "  手动下载方法:"
        echo "    HF_ENDPOINT=https://hf-mirror.com python3 -c \\"
        echo "      \"from huggingface_hub import snapshot_download; \\"
        echo "       snapshot_download('sentence-transformers/${MODEL_NAME}', \\"
        echo "         local_dir='~/.cache/huggingface/hub/models--sentence-transformers--${MODEL_NAME}')\""
        echo ""
        exit 1
    fi
}

check_ngrok_token() {
    if [ -z "$NGROK_AUTH_TOKEN" ] || [ "$NGROK_AUTH_TOKEN" = "your_ngrok_token_here" ]; then
        return 1
    fi
    return 0
}

# ────────────────────────────────────────
# 部署命令
# ────────────────────────────────────────

cmd_deploy() {
    local use_ngrok="${1:-yes}"

    print_banner
    check_docker
    check_env
    check_vectordb
    check_model_cache

    echo ""
    echo "  部署配置:"
    echo "    Robot ID    : ${WORKTOOL_ROBOT_ID:0:12}..."
    echo "    向量数据库   : Milvus Lite (milvus.db) + ChromaDB 降级备选"
    echo "    Flask 端口  : ${FLASK_PORT:-5000}"
    if [ "$use_ngrok" = "yes" ]; then
        echo "    ngrok       : 启用"
    else
        echo "    ngrok       : 禁用 (手动配置回调地址)"
    fi
    echo ""

    if [ "${1:-}" != "quick" ]; then
        read -p "  确认部署? [Y/n] " -r
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            echo "  已取消"
            exit 0
        fi
    fi

    echo ""
    echo "  [1/3] 构建 Docker 镜像..."

    # 构建 Docker 镜像（ngrok 和 lili-bot 共用一个 compose 文件）
    docker compose build --progress=plain

    echo ""
    echo "  [2/3] 启动服务..."

    if [ "$use_ngrok" = "yes" ] && check_ngrok_token; then
        docker compose up -d
        echo ""
        echo -e "${GREEN}  [✓] Lili Bot + ngrok 已启动${NC}"
        echo ""
        echo "  获取 ngrok 公网地址:"
        echo "    curl -s http://localhost:4040/api/tunnels | python3 -c \"import sys,json; d=json.load(sys.stdin); print(d['tunnels'][0]['public_url'])\""
        echo ""
    else
        docker compose up -d lili-bot
        echo ""
        echo -e "${GREEN}  [✓] Lili Bot 已启动${NC}"
        echo ""
        if [ "$use_ngrok" = "yes" ]; then
            echo -e "${YELLOW}  [!] ngrok 未启动（缺少 NGROK_AUTH_TOKEN），请手动配置回调地址${NC}"
            echo ""
        fi
    fi

    echo ""
    echo "  [3/3] 验证服务（等待模型加载，最长 90 秒）..."

    local wait_ok=0
    for i in $(seq 1 18); do
        if curl -sf http://localhost:5000/health > /dev/null 2>&1; then
            wait_ok=1
            break
        fi
        sleep 5
        echo "    等待中... ($((i * 5))s)"
    done
    if [ "$wait_ok" -eq 1 ]; then
        echo -e "${GREEN}  [✓] 健康检查通过!${NC}"
        echo ""
        echo -e "${BLUE}╔═══════════════════════════════════════════════════╗${NC}"
        echo -e "${BLUE}║              🎉 部署成功!                        ║${NC}"
        echo -e "${BLUE}╚═══════════════════════════════════════════════════╝${NC}"
        echo ""
        echo "  下一步 — 配置 WorkTool 回调:"
        echo "  1. 登录 https://console.worktool.ymdyes.cn"
        echo "  2. AI 引擎 → 新建 → 类型选 OpenClaw → Base URL 填你的 ngrok/公网地址"
        echo "  3. 机器人回调配置 → 填入 https://你的地址/worktool-callback"
        echo ""
        echo "  常用命令:"
        echo "    ./deploy.sh logs     # 查看日志"
        echo "    ./deploy.sh status   # 服务状态"
        echo "    ./deploy.sh stop     # 停止服务"
        echo ""
    else
        echo -e "${RED}  [✗] 健康检查失败，请查看日志:${NC}"
        echo "    ./deploy.sh logs"
        docker compose logs --tail=30 lili-bot
        exit 1
    fi
}

cmd_stop() {
    echo "停止服务..."
    docker compose down
    echo -e "${GREEN}[✓] 服务已停止${NC}"
}

cmd_logs() {
    docker compose logs -f --tail=50 lili-bot
}

cmd_status() {
    echo ""
    echo "=== 容器状态 ==="
    docker compose ps
    echo ""
    echo "=== 健康检查 ==="
    if curl -sf http://localhost:5000/health > /dev/null 2>&1; then
        curl -s http://localhost:5000/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:5000/health
    else
        echo -e "${RED}服务不可达${NC}"
    fi
    echo ""
    echo "=== 最近日志 ==="
    docker compose logs --tail=10 lili-bot
    echo ""
}

cmd_update() {
    echo "更新 Lili Bot..."
    check_model_cache
    docker compose down
    docker compose build --no-cache --progress=plain lili-bot
    docker compose up -d
    echo -e "${GREEN}[✓] 更新完成${NC}"
    echo "查看日志: ./deploy.sh logs"
}

# ────────────────────────────────────────
# 入口
# ────────────────────────────────────────

case "${1:-}" in
    quick)
        cmd_deploy "yes"
        ;;
    stop)
        cmd_stop
        ;;
    logs)
        cmd_logs
        ;;
    status)
        cmd_status
        ;;
    no-ngrok)
        cmd_deploy "no"
        ;;
    update)
        cmd_update
        ;;
    help|--help|-h)
        echo "用法: ./deploy.sh [命令]"
        echo ""
        echo "命令:"
        echo "  (无)        交互式部署（推荐）"
        echo "  quick       快速部署（跳过确认）"
        echo "  no-ngrok    不使用 ngrok 部署"
        echo "  stop        停止服务"
        echo "  logs        查看日志"
        echo "  status      查看状态"
        echo "  update      更新并重启"
        echo "  help        显示帮助"
        ;;
    *)
        cmd_deploy "yes"
        ;;
esac
