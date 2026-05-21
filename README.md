# IFA 上牌小助手 (Lili Bot)

> 企业微信 WorkTool 群消息 AI 助手 — 上牌流程引导、知识库问答、Docker 一键部署  
> **v1.3.0**

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![Milvus](https://img.shields.io/badge/Milvus-Lite-00A6D6.svg)](https://milvus.io/)

## 目录

- [功能概览](#功能概览)
- [快速开始](#快速开始)
- [常用命令](#常用命令)
- [配置说明](#配置说明)
- [本地开发](#本地开发)
- [更新知识库](#更新知识库)
- [项目结构](#项目结构)
- [故障排查](#故障排查)

---

## 功能概览

| 功能 | 触发方式 | 说明 |
|------|----------|------|
| 进群欢迎 + 上牌申请识别 | 群里出现「上牌申请」+「姓名」 | 解析顾问信息 → 发欢迎语 → 询问是否上过牌 |
| 上牌指引 | 上一步后回复是否有牌 | 无牌 → 推送资料清单；有牌 → 跳过 |
| RAG 智能问答 | @Lili 提问 | Milvus 向量检索 → 精准回答 |

---

## 快速开始

### 你需要

- 一台 Linux 服务器（建议 2C/2G 以上）
- [Docker](https://docs.docker.com/get-docker/) + Docker Compose
- WorkTool 机器人 robotId（[控制台](https://console.worktool.ymdyes.cn) 获取）
- （可选）[ngrok](https://ngrok.com) 账号（没有公网 IP 的话）

### 部署

```bash
git clone git@github.com:szzhangkkk/ifa-licensing-assistant.git
cd ifa-licensing-assistant

# 配置（只需填 WORKTOOL_ROBOT_ID）
cp .env.example .env
nano .env

# 一键部署
./deploy.sh
```

脚本自动完成：环境检查 → 下载模型 → 构建镜像 → 启动服务 → 健康检查。  
首次约 5-15 分钟（下载依赖 + 构建），后续更新 < 2 分钟（缓存命中）。

### 配置 WorkTool 回调

1. 登录 [WorkTool 控制台](https://console.worktool.ymdyes.cn)
2. **AI 引擎** → 新建 → 类型选 **OpenClaw**
3. **机器人回调** → `https://你的地址/worktool-callback`

获取公网地址（ngrok 用户）：

```bash
curl -s http://localhost:4040/api/tunnels | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(d['tunnels'][0]['public_url'])
"
```

---

## 常用命令

```bash
./deploy.sh logs      # 实时日志
./deploy.sh status    # 服务状态 + 健康检查
./deploy.sh stop      # 停止
./deploy.sh restart   # 重启（不重新构建）
./deploy.sh update    # 重新构建 + 重启
./deploy.sh help      # 查看所有命令
```

---

## 配置说明

| 变量 | 必需 | 说明 | 默认值 |
|------|:--:|------|--------|
| `WORKTOOL_ROBOT_ID` | **是** | WorkTool 机器人 ID | — |
| `NGROK_AUTH_TOKEN` | 推荐 | ngrok 认证令牌 | — |
| `FLASK_PORT` | 否 | 监听端口 | `5000` |
| `SUBMIT_EMAIL` | 否 | 资料提交邮箱 | `license@example.com` |

---

## 本地开发

```bash
pip install -r requirements.txt
cp .env.example .env
nano .env              # 填入 WORKTOOL_ROBOT_ID
python3 app.py         # http://localhost:5000
```

---

## 更新知识库

```bash
# 1. 编辑知识源文档
vim Agent5-Lili_cleaned.md

# 2. 重建向量库
python3 rebuild_kb_v2.py

# 3. 重新部署
./deploy.sh update
```

---

## 项目结构

```
ifa-licensing-assistant/
├── app.py                     # ★ 主程序（Flask + RAG + 状态机）
├── deploy.sh                  # ★ 一键部署脚本
├── Dockerfile
├── docker-compose.yml
├── .env.example               # 环境变量模板
├── requirements.txt
├── milvus.db                  # Milvus Lite 预构建知识库
├── chroma_db/                 # ChromaDB 降级备选
├── rebuild_kb_v2.py           # 知识库重建脚本
├── Agent5-Lili_cleaned.md     # 知识源文档
└── ifa_*.py                   # 功能模块脚本
```

---

## 故障排查

### 部署相关

| 现象 | 原因 | 解决 |
|------|------|------|
| 服务启动失败 | `.env` 未配置 | `cp .env.example .env` 并填入 `WORKTOOL_ROBOT_ID` |
| `docker compose build` 失败 | milvus.db 不存在 | `python3 rebuild_kb_v2.py` |
| 构建时报 pip/apt 下载失败 | 网络问题 | Dockerfile 已配置清华源 + 阿里云镜像，重试即可 |
| 容器不断重启 | 内存不足 | 确认服务器 ≥ 1.5G 可用内存 |

### 功能相关

| 现象 | 原因 | 解决 |
|------|------|------|
| 机器人不回复 | 回调地址不对 | 检查 ngrok 地址 → 更新 WorkTool 后台 |
| 回复乱码 | AI 引擎类型不是 OpenClaw | WorkTool 后台改为 OpenClaw |
| API 返回 501 | 机器人不在线 | 确保 WTApp 在线 |
| 功能二不发资料 | pending 状态残留 | 进入容器执行 `rm /tmp/ifa_pending_license_reply.txt` |

---

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/` | 服务信息 |
| `GET` | `/health` | 健康检查（含向量数据库状态） |
| `POST` | `/worktool-callback` | WorkTool 消息回调 |

---

## 技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | Flask 3.x |
| 向量数据库 | Milvus Lite 3.0 + ChromaDB 1.5 |
| Embedding | paraphrase-multilingual-MiniLM-L12-v2 |
| 容器化 | Docker + Compose |
| 内网穿透 | ngrok |

## 许可证

MIT
