# IFA 上牌小助手 (Lili Bot)

> 企业微信 WorkTool 群消息 AI 助手 — 支持上牌流程引导、知识库问答、Docker 一键部署

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

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
| 功能一 | 进群欢迎 + 上牌申请识别 | 群里出现「上牌申请」+「姓名」格式消息 | 自动解析顾问信息 → 发欢迎语 → 询问是否上过牌 |
| 功能二 | 上牌指引（有牌/无牌分支） | 功能一询问后，顾问回复是否有牌 | 无牌 → 推送完整资料清单；有牌 → 跳过，后续直接问答 |
| 功能六 | RAG 智能问答 | @Lili 提问上牌相关问题 | 从 ChromaDB 知识库检索相关内容，生成精准回答 |

**状态机流程：**

```
新顾问入群发「上牌申请」
       ↓
  [功能一] 解析姓名/学历/推荐人 → 发欢迎语1+2 → 问「是否上过牌」
       ↓
  顾问回复
       ↓
  [功能二] 判断:
    ├─ 「没有上过牌」→ 推送资料清单(1/2/3) → 完成
    ├─ 「有牌/已上牌」→ 跳过，直接进入问答模式
    └─ 模糊回答 → 继续等待明确回复
       ↓
  后续任何 @Lili 提问
       ↓
  [功能六] RAG 检索 → 智能回复
```

---

## 快速部署（Docker 推荐）

### 前置条件

- [Docker](https://docs.docker.com/get-docker/) + Docker Compose
- WorkTool 账号 + 机器人 robotId（[控制台](https://console.worktool.ymdyes.cn) 获取）
- （可选）[ngrok](https://ngrok.com) 免费账号，用于内网穿透

### 步骤

```bash
# 1. 克隆仓库
git clone git@github.com:szzhangkkk/ifa-licensing-assistant.git
cd ifa-licensing-assistant

# 2. 配置环境变量（只需填 WORKTOOL_ROBOT_ID）
cp .env.example .env
nano .env   # 填入你的 robotId

# 3. 一键部署
./deploy.sh
```

脚本自动完成：环境检查 → 配置引导 → 镜像构建 → 服务启动 → 健康验证。

如果服务器已有公网 IP，不需要 ngrok：

```bash
./deploy.sh no-ngrok
```

### 配置 WorkTool 回调

部署成功后，登录 [WorkTool 控制台](https://console.worktool.ymdyes.cn) 配置：

1. **AI 引擎** → 新建 → **类型选 OpenClaw** → Base URL 填你的公网地址（ngrok 或服务器 IP:5000）
2. **机器人回调** → 填入 `https://你的地址/worktool-callback`
3. 确认机器人在 WTApp 中处于**在线**状态

> 注意：免费版 ngrok 每次重启地址会变，记得同步更新 WorkTool 后台的 Base URL。

获取当前 ngrok 地址：

```bash
curl -s http://localhost:4040/api/tunnels | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(d['tunnels'][0]['public_url'])
"
```

### 常用命令

```bash
./deploy.sh logs      # 查看实时日志
./deploy.sh status    # 查看服务状态 + 健康检查
./deploy.sh stop      # 停止所有服务
./deploy.sh update    # 拉取最新代码 + 重新构建 + 重启
```

---

## 手动部署

适用于无 Docker 环境的场景。

### 环境要求

- Python **3.12** 或更高版本
- 至少 2GB 可用内存（ChromaDB + embedding 模型）

### 步骤

```bash
# 1. 安装 Python 依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
nano .env  # 填入 WORKTOOL_ROBOT_ID

# 3. 启动服务
python3 app.py
```

### 生产环境（Gunicorn）

```bash
pip install gunicorn
gunicorn app:app -b 0.0.0.0:5000 -w 2 --access-logfile -
```

### 配合 ngrok（手动）

```bash
# 终端1：启动 Flask
python3 app.py

# 终端2：启动 ngrok 隧道
ngrok http 5000
```

---

## 配置说明

所有配置通过 `.env` 文件或环境变量管理：

| 变量 | 必需 | 说明 | 默认值 |
|------|:--:|------|--------|
| `WORKTOOL_ROBOT_ID` | **是** | WorkTool 机器人 ID | — |
| `WORKTOOL_API_URL` | 否 | WorkTool API 地址 | 官方 API |
| `NGROK_AUTH_TOKEN` | 推荐 | ngrok 认证令牌 | — |
| `CHROMA_DB_PATH` | 否 | 向量数据库路径 | `./chroma_db` |
| `CHROMA_COLLECTION` | 否 | ChromaDB Collection 名称 | `ifa_licensing_kb` |
| `FLASK_PORT` | 否 | 监听端口 | `5000` |
| `FLASK_HOST` | 否 | 绑定地址 | `0.0.0.0` |
| `SUBMIT_EMAIL` | 否 | 资料提交邮箱 | `license@example.com` |
| `A1_FORM_URL` | 否 | A1 表格 PDF 链接 | 语雀 |
| `A1_GUIDE_URL` | 否 | A1 签署指引 PDF 链接 | 语雀 |
| `WECOM_BOT_ID` | 否 | 企业微信 AI Bot ID（SDK 长连接用） | — |
| `WECOM_BOT_SECRET` | 否 | 企业微信 AI Bot Secret（SDK 用） | — |

---

## 架构设计

```
┌─────────────────────────────────────────────────┐
│              企业微信群聊                          │
│    @Lili 提问  /  上牌申请  /  回复是否上过牌       │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│           WorkTool 机器人 (WTApp 在线)             │
│    AI 引擎: OpenClaw → POST 到 ngrok 地址         │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│            ngrok 内网穿透 (可选)                    │
│    https://xxxx.ngrok-free.app → localhost:5000 │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│         Flask 回调服务器 (app.py :5000)            │
│                                                  │
│   ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│   │  功能一   │  │  功能二   │  │    功能六     │ │
│   │ 欢迎流程  │→ │ 上牌指引  │→ │  RAG 问答     │ │
│   └──────────┘  └──────────┘  └──────┬───────┘ │
│                                       │          │
│                              ChromaDB 检索       │
│                              (25 chunks)         │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│      WorkTool API (sendRawMessage)               │
│      POST → 消息回复到群里                         │
└─────────────────────────────────────────────────┘
```

**关键技术点：**
- AI 引擎类型必须设为 **OpenClaw**（不是 OpenAI），否则 AI 引擎会自己生成回复导致乱码
- 回调接口必须在 **3 秒内** 返回，否则 WorkTool 丢弃请求
- 机器人必须在 WTApp 保持**在线**，否则 API 返回 501
- ChromaDB 知识库使用 `paraphrase-multilingual-MiniLM-L12-v2` 做中文语义向量化

---

## 项目结构

```
ifa-licensing-assistant/
├── app.py                  # ★ 主程序（Flask + RAG + 状态机）
├── deploy.sh               # ★ 一键部署脚本
├── Dockerfile              # Docker 镜像定义
├── docker-compose.yml      # 编排文件（lili-bot + ngrok）
├── .env.example            # 配置模板
├── .gitignore
├── .dockerignore
├── requirements.txt        # Python 依赖清单
├── README.md               # 本文档
│
├── chroma_db/              # 预构建向量知识库（25 chunks）
│   ├── chroma.sqlite3
│   └── <uuid>/
│       ├── data_level0.bin
│       ├── header.bin
│       ├── length.bin
│       └── link_lists.bin
│
├── Agent5-Lili_cleaned.md  # 知识源文档（已清理隐私信息）
├── rebuild_kb_v2.py        # 知识库重建脚本
│
├── ifa_welcome_flow.py     # 功能一：进群欢迎 + 上牌申请解析
├── ifa_doc_push.py         # 功能二：资料推送
├── ifa_ia_guide.py         # 功能三：IA 系统指引
├── ifa_email_setup.py      # 功能四：邮箱开设
├── ifa_training_reminder.py# 功能五：培训提醒
├── ifa_wecom_sender.py     # WorkTool API 发消息客户端
└── wecom_sdk_long_connection.py  # 企业微信 WebSocket SDK
```

---

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/` | 服务信息 |
| `GET` | `/health` | 健康检查 |
| `POST` | `/worktool-callback` | WorkTool 消息回调入口 |

### 健康检查

```bash
curl http://localhost:5000/health
```

返回示例：

```json
{
    "status": "ok",
    "timestamp": "2026-05-14T15:13:25",
    "chroma_db": true,
    "robot_configured": true,
    "version": "1.0.0"
}
```

### 回调格式

WorkTool POST 到 `/worktool-callback` 的 JSON 字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `spoken` | string | 消息内容（去掉 @ 前缀） |
| `rawSpoken` | string | 原始消息 |
| `receivedName` | string | 发送者名称 |
| `groupName` | string | 群名称 |
| `roomType` | int | 3=群聊 |
| `atMe` | bool/string | 是否 @ 了机器人 |
| `textType` | int | 1=文本消息 |

---

## 故障排查

### 服务启动失败

```bash
# 查看日志
./deploy.sh logs
docker compose logs lili-bot
```

| 现象 | 原因 | 解决 |
|------|------|------|
| `WORKTOOL_ROBOT_ID 未配置` | `.env` 未设置 | 编辑 `.env` 填入正确的 robotId |
| `知识库路径不存在` | `chroma_db/` 缺失 | 确认目录存在，或运行 `python3 rebuild_kb_v2.py` 重建 |
| `ModuleNotFoundError` | 依赖未安装 | `pip install -r requirements.txt` |

### 消息发不出去 / 无回复

| 现象 | 原因 | 解决 |
|------|------|------|
| 群里无任何回复 | ngrok 或 Flask 不可达 | 检查 `curl http://localhost:5000/health` |
| 回复乱码/模板内容 | AI 引擎类型不是 OpenClaw | WorkTool 后台改 AI 引擎类型为 **OpenClaw** |
| API 返回 501 | 机器人不在线 | 在 WTApp 中确保 Lili 在线 |
| 功能一触发但功能二不发资料 | pending 状态残留 | 清空 `/tmp/ifa_pending_license_reply.txt` 后重试 |

### ngrok 相关

| 现象 | 解决 |
|------|------|
| 地址每次重启变化 | 免费版限制，更新 WorkTool 后台的 Base URL |
| `ngrok not found` | Docker Compose 中自动处理；手动则需 `brew install ngrok` 或下载 |

### ChromaDB 知识库问题

```bash
# 检查知识库状态
python3 -c "
import chromadb
c = chromadb.PersistentClient(path='./chroma_db')
coll = c.get_collection('ifa_licensing_kb')
print(f'Chunks: {coll.count()}')
"

# 重建知识库（需要源文档 Agent5-Lili_cleaned.md）
python3 rebuild_kb_v2.py
```

---

## 更新知识库

当上牌政策、资料清单或话术模板有变更时：

```bash
# 1. 更新源文档 Agent5-Lili_cleaned.md

# 2. 重建向量数据库
python3 rebuild_kb_v2.py

# 3. 重新构建 Docker 镜像并重启
./deploy.sh update
```

---

## 开发指南

### 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 设置环境变量（测试用）
export WORKTOOL_ROBOT_ID=your_test_id

# 启动开发服务器
python3 app.py
```

### 代码结构

- `app.py` — 唯一入口，包含所有核心逻辑
  - `callback()` — `/worktool-callback` 端点，消息分发
  - `generate_reply()` — 回复生成（关键词 + RAG）
  - `rag_reply()` — ChromaDB 检索
  - `send_to_worktool()` — WorkTool API 发消息
  - 功能一/二状态机内联在 callback 中

### 测试

```bash
# 健康检查
curl http://localhost:5000/health

# 模拟回调（功能六测试）
curl -X POST http://localhost:5000/worktool-callback \
  -H "Content-Type: application/json" \
  -d '{"spoken":"上牌需要什么材料","receivedName":"测试用户","groupName":"test群","atMe":true,"textType":1}'

# 模拟上牌申请（功能一测试）
curl -X POST http://localhost:5000/worktool-callback \
  -H "Content-Type: application/json" \
  -d '{"spoken":"上牌申请\n姓名：测试\n学历：本科","receivedName":"测试用户","groupName":"test群","atMe":true,"textType":1}'
```

---

## 技术栈

| 组件 | 技术 | 版本 |
|------|------|------|
| Web 框架 | Flask | 3.x |
| 向量数据库 | ChromaDB | 1.5.x |
| Embedding 模型 | paraphrase-multilingual-MiniLM-L12-v2 | — |
| 容器化 | Docker + Compose | — |
| 内网穿透 | ngrok | 免费版 |
| Python | 3.12 | — |

## 许可证

MIT License
