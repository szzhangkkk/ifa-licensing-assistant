# IFA 上牌小助手 (Lili Bot)

> 企业微信 WorkTool 群消息 AI 助手 — 支持上牌流程引导、知识库问答、Docker 一键部署  
> **v1.3.0 — 预构建 ACR 镜像部署，Milvus Lite 向量检索引擎**

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![Milvus](https://img.shields.io/badge/Milvus-Lite-00A6D6.svg)](https://milvus.io/)

## 目录

- [功能概览](#功能概览)
- [快速部署（Docker 推荐）](#快速部署docker-推荐)
- [手动部署](#手动部署)
- [配置说明](#配置说明)
- [架构设计](#架构设计)
- [项目结构](#项目结构)
- [API 端点](#api-端点)
- [故障排查](#故障排查)
- [更新知识库](#更新知识库)
- [开发指南](#开发指南)

---

## 功能概览

| 功能编号 | 功能名称 | 触发方式 | 说明 |
|----------|----------|----------|------|
| 功能一 | 进群欢迎 + 上牌申请识别 | 群里出现「上牌申请」+「姓名」 | 自动解析顾问信息 → 发欢迎语 → 询问是否上过牌 |
| 功能二 | 上牌指引（有牌/无牌分支） | 功能一后回复是否有牌 | 无牌 → 推送完整资料清单；有牌 → 跳过 |
| 功能六 | RAG 智能问答 | @Lili 提问 | Milvus 向量检索 → 精准回答 |

**状态机流程：**

```
新顾问入群发「上牌申请」
       ↓
  [功能一] 解析信息 → 欢迎语 → 询问「是否上过牌」
       ↓
  [功能二] 判断: 无牌→推送资料 / 有牌→跳过 / 模糊→等待
       ↓
  [功能六] @Lili 提问 → Milvus 检索 → 回复
```

---

## 快速部署（Docker 推荐）

### 前置条件

- [Docker](https://docs.docker.com/get-docker/) + Docker Compose
- WorkTool 机器人 robotId（[控制台](https://console.worktool.ymdyes.cn) 获取）
- （可选）[ngrok](https://ngrok.com) 账号

### 步骤

```bash
git clone git@github.com:szzhangkkk/ifa-licensing-assistant.git
cd ifa-licensing-assistant

# 配置（只需填 ROBOT_ID）
cp .env.example .env
nano .env

# 一键部署（自动从 ACR 拉取预构建镜像 + 启动）
./deploy.sh
```

脚本自动完成：环境检查 → 配置引导 → **从 ACR 拉取镜像** → 服务启动 → 健康验证。  
部署时间：首次 2-5 分钟（拉取完整镜像），后续更新 < 30 秒。

> 镜像托管在阿里云 ACR（`registry.cn-hangzhou.aliyuncs.com/ifa/lili-bot`），国内直连，无需 Docker Hub 加速器。

### 配置 WorkTool 回调

1. 登录 [WorkTool 控制台](https://console.worktool.ymdyes.cn)
2. **AI 引擎** → 新建 → 类型选 **OpenClaw** → Base URL 填公网地址
3. **机器人回调** → `https://你的地址/worktool-callback`

获取 ngrok 地址：
```bash
curl -s http://localhost:4040/api/tunnels | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(d['tunnels'][0]['public_url'])
"
```

### 常用命令

```bash
./deploy.sh logs      # 实时日志
./deploy.sh status    # 服务状态 + 镜像信息
./deploy.sh stop      # 停止
./deploy.sh restart   # 重启（不拉取新镜像）
./deploy.sh update    # 拉取最新镜像 + 重启
```

---

## 构建与发布（在构建机上操作）

当代码或知识库更新后，重新构建镜像并推送到 ACR：

```bash
# 前提：已登录 ACR
docker login --username=你的阿里云账号 registry.cn-hangzhou.aliyuncs.com

# 一键构建 + 推送
./deploy.sh push

# 或分步操作
./deploy.sh build                                      # 本地构建
docker tag ifa-lili-bot:latest registry.cn-hangzhou.aliyuncs.com/ifa/lili-bot:latest
docker push registry.cn-hangzhou.aliyuncs.com/ifa/lili-bot:latest
```

部署端执行 `./deploy.sh` 即可拉取最新镜像。

> 首次推送前请在阿里云 [容器镜像服务](https://cr.console.aliyun.com) 创建命名空间 `ifa`（个人版免费）。

---

## 手动部署

```bash
pip install -r requirements.txt
cp .env.example .env  # 编辑填入 WORKTOOL_ROBOT_ID
python3 app.py
```

生产环境：
```bash
gunicorn app:app -b 0.0.0.0:5000 -w 2 --access-logfile -
```

---

## 配置说明

| 变量 | 必需 | 说明 | 默认值 |
|------|:--:|------|--------|
| `WORKTOOL_ROBOT_ID` | **是** | WorkTool 机器人 ID | — |
| `REGISTRY` | 否 | 镜像仓库地址 | `registry.cn-hangzhou.aliyuncs.com` |
| `IMAGE_NAMESPACE` | 否 | 镜像命名空间 | `ifa` |
| `IMAGE_TAG` | 否 | 镜像版本标签 | `latest` |
| `MILVUS_DB_PATH` | 否 | Milvus Lite 数据库路径 | `./milvus.db` |
| `CHROMA_DB_PATH` | 否 | ChromaDB 降级备选路径 | `./chroma_db` |
| `NGROK_AUTH_TOKEN` | 推荐 | ngrok 认证令牌 | — |
| `FLASK_PORT` | 否 | 监听端口 | `5000` |
| `SUBMIT_EMAIL` | 否 | 资料提交邮箱 | `license@example.com` |

**向量数据库策略：** Milvus Lite 优先，不可用时自动降级到 ChromaDB。无需额外配置。

---

## 架构设计

```
群里 @Lili 提问
      ↓
  WorkTool 机器人 (AI引擎: OpenClaw)
      ↓
  ngrok 隧道
      ↓
  Flask 回调服务器 (:5000)
      ├── 功能一：上牌申请识别 → 欢迎语
      ├── 功能二：上牌指引（有牌/无牌）
      └── 功能六：RAG 问答
            ↓
      ┌─ Milvus Lite 向量检索 (优先)
      └─ ChromaDB 降级 (备选)
            ↓
  WorkTool API → 回复到群里
```

**技术栈：** Flask · Milvus Lite · ChromaDB · Sentence Transformers · Docker · ngrok

---

## 项目结构

```
ifa-licensing-assistant/
├── app.py                  # ★ 主程序（Flask + RAG + 状态机）
├── deploy.sh               # ★ 一键部署/构建/推送脚本
├── Dockerfile
├── docker-compose.yml      # 部署端：拉取 ACR 镜像
├── docker-compose.build.yml # 构建机：本地构建镜像
├── .env.example / requirements.txt
├── milvus.db               # ★ Milvus Lite 预构建知识库 (25 chunks)
├── chroma_db/              # ChromaDB 降级备选
├── rebuild_kb_v2.py        # 知识库重建脚本 (Milvus)
├── Agent5-Lili_cleaned.md  # 知识源文档
└── ifa_*.py                # 功能脚本
```

---

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/` | 服务信息 |
| `GET` | `/health` | 健康检查（含向量数据库状态） |
| `POST` | `/worktool-callback` | WorkTool 消息回调 |

```bash
curl http://localhost:5000/health
# {"status":"ok","vector_db":"milvus","milvus_db":true,...}
```

---

## 故障排查

| 现象 | 原因 | 解决 |
|------|------|------|
| 服务启动失败 | `.env` 未配置 | 编辑 `.env` 填入 `WORKTOOL_ROBOT_ID` |
| `docker compose pull` 很慢/失败 | 未登录 ACR | `docker login --username=阿里云账号 registry.cn-hangzhou.aliyuncs.com` |
| 知识库未找到 | milvus.db 不存在 | `python3 rebuild_kb_v2.py` |
| `./deploy.sh build` 失败 | hf_model_cache/ 或 milvus.db 缺失 | 部署端不再需要 build，可直接 pull |
| 回复乱码 | AI 引擎类型不是 OpenClaw | WorkTool 后台改为 OpenClaw |
| API 返回 501 | 机器人不在线 | WTApp 确保在线 |
| 功能二不发资料 | pending 状态残留 | 清空 `/tmp/ifa_pending_license_reply.txt` |
| Milvus 不可用 | 自动降级 ChromaDB | 无需操作，日志会有提示 |

---

## 更新知识库

```bash
# 1. 更新源文档 Agent5-Lili_cleaned.md
# 2. 重建知识库
python3 rebuild_kb_v2.py
# 3. 构建 + 推送新镜像（在构建机上）
./deploy.sh push
# 4. 部署端拉取新镜像
./deploy.sh update
```

---

## 技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | Flask 3.x |
| 向量数据库 | Milvus Lite 3.0 (优先) + ChromaDB 1.5 (降级) |
| Embedding | paraphrase-multilingual-MiniLM-L12-v2 |
| 容器化 | Docker + Compose |
| 内网穿透 | ngrok |

## 许可证

MIT
