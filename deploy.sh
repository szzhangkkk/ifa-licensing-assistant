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
    echo -e "${BLUE}║                v1.0.0                            ║${NC}"
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
    if [ -f "milvus.db" ]; then
        echo -e "${GREEN}[✓] 知识库已就绪 (Milvus Lite: milvus.db)${NC}"
    elif [ -d "chroma_db" ] && [ -f "chroma_db/chroma.sqlite3" ]; then
        echo -e "${YELLOW}[!] 使用 ChromaDB 降级方案 (chroma_db/)，建议迁移到 Milvus: python3 rebuild_kb_v2.py${NC}"
    else
        echo ""
        echo -e "${RED}[错误] 向量数据库未找到!${NC}"
        echo ""
        echo "  请先构建知识库:"
        echo "    python3 rebuild_kb_v2.py"
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

    echo ""
    echo "  部署配置:"
    echo "    Robot ID    : ${WORKTOOL_ROBOT_ID:0:12}..."
    echo "    知识库路径   : $SCRIPT_DIR/chroma_db"
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

    # 根据是否使用 ngrok 选择 compose 文件
    if [ "$use_ngrok" = "yes" ] && check_ngrok_token; then
        docker compose build lili-bot
    else
        # 不使用 ngrok 时只启动 lili-bot
        docker compose build lili-bot
    fi

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
    echo "  [3/3] 验证服务..."

    sleep 3
    if curl -sf http://localhost:5000/health > /dev/null 2>&1; then
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
    docker compose down
    docker compose build --no-cache lili-bot
    docker compose up -d lili-bot
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
