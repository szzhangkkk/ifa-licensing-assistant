# IFA 上牌小助手 (Lili Bot)

> 企业微信 WorkTool 群消息 AI 助手 — 上牌流程引导、知识库问答、Docker 一键部署  
> **v1.3.0 — 预构建 ACR 镜像，国内直连，< 1 分钟部署**

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![Milvus](https://img.shields.io/badge/Milvus-Lite-00A6D6.svg)](https://milvus.io/)

## 目录

- [功能概览](#功能概览)
- [快速开始（Docker 部署）](#快速开始docker-部署)
- [配置 WorkTool 回调](#配置-worktool-回调)
- [常用命令](#常用命令)
- [配置说明](#配置说明)
- [部署架构](#部署架构)
- [构建与发布](#构建与发布)
- [本地开发](#本地开发)
- [更新知识库](#更新知识库)
- [API 端点](#api-端点)
- [项目结构](#项目结构)
- [故障排查](#故障排查)

---

## 功能概览

| 功能 | 触发方式 | 说明 |
|------|----------|------|
| 进群欢迎 + 上牌申请识别 | 群里出现「上牌申请」+「姓名」 | 自动解析顾问信息 → 发欢迎语 → 询问是否上过牌 |
| 上牌指引（有牌/无牌） | 上一步后回复是否有牌 | 无牌 → 推送完整资料清单；有牌 → 跳过 |
| RAG 智能问答 | @Lili 提问 | Milvus 向量检索 → 精准回答 |

**流程：**

```
新顾问入群发「上牌申请」
       ↓
  解析信息 → 欢迎语 → 询问「是否上过牌」
       ↓
  判断: 无牌→推送资料 / 有牌→跳过
       ↓
  @Lili 提问 → Milvus 检索 → 回复
```

---

## 快速开始（Docker 部署）

### 你需要准备

| 项目 | 说明 | 获取方式 |
|------|------|----------|
| 一台 Linux 服务器 | 建议 2C/2G 以上 | 阿里云/腾讯云/本地均可 |
| Docker + Compose | 容器运行环境 | `curl -fsSL https://get.docker.com \| sh` |
| WorkTool 机器人 | robotId | [WorkTool 控制台](https://console.worktool.ymdyes.cn) → 机器人配置 |
| 阿里云账号 | 拉取镜像用（免费） | [注册阿里云](https://www.aliyun.com) |
| ngrok 账号 | 内网穿透（可选） | [注册 ngrok](https://ngrok.com) |

### 三步部署

```bash
# 1. 拉取代码
git clone git@github.com:szzhangkkk/ifa-licensing-assistant.git
cd ifa-licensing-assistant

# 2. 配置 .env（只需填 WORKTOOL_ROBOT_ID，其他保持默认）
cp .env.example .env
nano .env

# 3. 一键部署
./deploy.sh
```

脚本自动完成：**登录 ACR → 拉取镜像 → 启动服务 → 健康检查**。

> 首次部署需要登录阿里云 ACR，脚本会提示你输入账号密码。  
> 阿里云容器镜像服务个人版完全免费，只用来拉镜像，无需额外配置。

部署成功后你应该看到：

```
[✓] 健康检查通过!
🎉 部署成功!
```

接下来去 WorkTool 后台配置回调地址。

---

## 配置 WorkTool 回调

1. 登录 [WorkTool 控制台](https://console.worktool.ymdyes.cn)
2. **AI 引擎** → 新建
   - 类型选 **OpenClaw**（重要！选错会导致回复乱码）
   - Base URL 填你的公网地址
3. **机器人回调** → `https://你的地址/worktool-callback`

**获取公网地址（ngrok 用户）：**

```bash
curl -s http://localhost:4040/api/tunnels | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(d['tunnels'][0]['public_url'])
"
```

> 免费版 ngrok 每次重启地址会变，需要重新配置 WorkTool 回调。有公网 IP 的服务器可去掉 ngrok，直接 `./deploy.sh no-ngrok`。

---

## 常用命令

```bash
./deploy.sh logs      # 实时日志
./deploy.sh status    # 服务状态 + 镜像信息 + 健康检查
./deploy.sh stop      # 停止
./deploy.sh restart   # 重启（不拉取新镜像）
./deploy.sh update    # 拉取最新镜像 + 重启
./deploy.sh help      # 查看所有命令
```

---

## 配置说明

| 变量 | 必需 | 说明 | 默认值 |
|------|:--:|------|--------|
| `WORKTOOL_ROBOT_ID` | **是** | WorkTool 机器人 ID | — |
| `REGISTRY` | 否 | 镜像仓库地址 | `registry.cn-hangzhou.aliyuncs.com` |
| `IMAGE_NAMESPACE` | 否 | 镜像命名空间 | `ifa` |
| `IMAGE_TAG` | 否 | 镜像版本（可固定版本回滚） | `latest` |
| `NGROK_AUTH_TOKEN` | 推荐 | ngrok 认证令牌 | — |
| `FLASK_PORT` | 否 | 监听端口 | `5000` |
| `SUBMIT_EMAIL` | 否 | 资料提交邮箱 | `license@example.com` |

---

## 部署架构

```
┌──────────────┐      ┌──────────────────┐      ┌──────────────┐
│  构建机       │ push │  阿里云 ACR       │ pull │  你的服务器   │
│  (开发者电脑)  │─────→│  registry.cn-    │←─────│              │
│              │      │  hangzhou.        │      │ ./deploy.sh  │
│ ./deploy.sh  │      │  aliyuncs.com/    │      │   = pull     │
│   push       │      │  ifa/lili-bot     │      │   + up -d    │
└──────────────┘      └──────────────────┘      └──────────────┘
                                                    │
                                                    ↓
                                              ┌──────────┐
                                              │  ngrok   │
                                              │  隧道    │
                                              └────┬─────┘
                                                   ↓
                                             WorkTool 回调
```

**关键点：**
- 镜像只需构建一次（在开发者电脑上），推送后所有服务器都能直接用
- 部署端不需要下载依赖、模型、知识库——全部打包在镜像里
- 国内直连阿里云 ACR，不走 Docker Hub，速度快且稳定
- 版本通过 `IMAGE_TAG` 控制，可随时回滚到旧版本

---

## 构建与发布

> 本节仅面向项目维护者。普通部署者无需关心，直接 `./deploy.sh` 即可。

### 首次设置（一次性）

1. 打开 [阿里云容器镜像服务](https://cr.console.aliyun.com)
2. 开通 **个人版**（免费）
3. 创建命名空间 `ifa`
4. 在「访问凭证」页面设置 Registry 密码

```bash
# 在构建机上登录
docker login --username=你的阿里云账号 registry.cn-hangzhou.aliyuncs.com
# 输入 Registry 密码（不是阿里云登录密码）
```

### 日常发布

```bash
# 代码或知识库更新后
./deploy.sh push        # 构建 + 推送（约 5-15 分钟）
```

### 多版本管理

```bash
# 构建时打多个标签
docker tag ifa-lili-bot:latest registry.cn-hangzhou.aliyuncs.com/ifa/lili-bot:v1.3.0
docker push registry.cn-hangzhou.aliyuncs.com/ifa/lili-bot:v1.3.0

# 部署端切换版本（在 .env 中设置）
IMAGE_TAG=v1.2.0 ./deploy.sh update    # 回滚到旧版本
IMAGE_TAG=latest ./deploy.sh update    # 回到最新版
```

### 同时推送 ngrok 镜像（可选）

如果部署端拉 ngrok 镜像也慢，可以把 ngrok 也推到 ACR：

```bash
docker pull ngrok/ngrok:latest
docker tag ngrok/ngrok:latest registry.cn-hangzhou.aliyuncs.com/ifa/ngrok:latest
docker push registry.cn-hangzhou.aliyuncs.com/ifa/ngrok:latest
```

---

## 本地开发

不依赖 Docker，直接在本地跑（需要 Python 3.12）：

```bash
pip install -r requirements.txt
cp .env.example .env
nano .env              # 填入 WORKTOOL_ROBOT_ID
python3 app.py         # http://localhost:5000
```

生产环境用 gunicorn：

```bash
gunicorn app:app -b 0.0.0.0:5000 -w 2 --access-logfile -
```

---

## 更新知识库

```bash
# 1. 编辑知识源文档
vim Agent5-Lili_cleaned.md

# 2. 重建向量库
python3 rebuild_kb_v2.py

# 3. 重新构建 + 推送镜像
./deploy.sh push

# 4. 部署端更新
# （在服务器上）
./deploy.sh update
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

## 项目结构

```
ifa-licensing-assistant/
├── app.py                     # ★ 主程序（Flask + RAG + 状态机）
├── deploy.sh                  # ★ 一键部署/构建/推送脚本
├── Dockerfile
├── docker-compose.yml         # 部署端：拉取 ACR 镜像
├── docker-compose.build.yml   # 构建机：本地构建镜像
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
| `pull` 报 `unauthorized` | 未登录 ACR | `docker login --username=阿里云账号 registry.cn-hangzhou.aliyuncs.com` |
| `pull` 很慢或超时 | 网络问题 | 检查是否能在服务器上 ping 通 `registry.cn-hangzhou.aliyuncs.com` |
| 服务启动失败 | `.env` 未配置 | `cp .env.example .env` 并填入 `WORKTOOL_ROBOT_ID` |
| 容器不断重启 | 内存不足 | 确认服务器 ≥ 1.5G 可用内存 |

### 功能相关

| 现象 | 原因 | 解决 |
|------|------|------|
| 机器人收到消息不回复 | 回调地址不对或 ngrok 地址变了 | 检查 ngrok 地址 → 更新 WorkTool 后台 |
| 回复乱码 | AI 引擎类型不是 OpenClaw | WorkTool 后台改为 OpenClaw |
| API 返回 501 | 机器人不在线 | 确保 WTApp 在线 |
| 功能二不发资料 | pending 状态残留 | 进入容器执行 `rm /tmp/ifa_pending_license_reply.txt` |
| 知识库搜不到内容 | milvus.db 需要更新 | 参考 [更新知识库](#更新知识库) |

---

## 技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | Flask 3.x |
| 向量数据库 | Milvus Lite 3.0（优先）+ ChromaDB 1.5（降级） |
| Embedding | paraphrase-multilingual-MiniLM-L12-v2 |
| 容器化 | Docker + Compose |
| 镜像仓库 | 阿里云 ACR（个人版免费） |
| 内网穿透 | ngrok |

## 许可证

MIT
