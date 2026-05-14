# IFA 上牌小助手 (Lili Bot)

企业微信 WorkTool 群消息 AI 助手，支持上牌流程引导和知识库问答。

## 功能一览

| 功能 | 说明 | 触发方式 |
|------|------|----------|
| 功能一 | 进群欢迎 + 上牌申请识别 | 群里出现「上牌申请」+「姓名」 |
| 功能二 | 上牌指引（有牌/无牌分支） | 功能一后回复「没有上过牌」等 |
| 功能六 | RAG 知识库问答 | @Lili 提问 |

## 快速开始（Docker 一键部署）

### 前置条件

- [Docker](https://docs.docker.com/get-docker/) 已安装
- WorkTool 账号 + 机器人 robotId
- （可选）[ngrok](https://ngrok.com) 账号（内网穿透用）

### 1. 获取代码

```bash
cd ifa_knowledge_base
```

### 2. 一键部署

```bash
./deploy.sh
```

脚本会自动：
1. 检查 Docker 环境
2. 引导你配置 `.env` 文件
3. 构建 Docker 镜像
4. 启动 Flask 服务器 + ngrok 隧道
5. 验证服务健康

如果不需要 ngrok（服务器有公网 IP），运行：

```bash
./deploy.sh no-ngrok
```

### 3. 配置 WorkTool 回调

部署成功后，需要配置 WorkTool 后台：

1. 登录 [WorkTool 控制台](https://console.worktool.ymdyes.cn)
2. **AI 引擎** → 新建 → 类型选 **OpenClaw**
3. Base URL 填入 `https://你的ngrok地址`（或你的公网 IP:5000）
4. **机器人回调配置** → 填入 `https://你的地址/worktool-callback`

获取 ngrok 公网地址：
```bash
curl -s http://localhost:4040/api/tunnels | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['tunnels'][0]['public_url'])"
```

### 4. 常用命令

```bash
./deploy.sh logs      # 查看实时日志
./deploy.sh status    # 查看服务状态
./deploy.sh stop      # 停止服务
./deploy.sh update    # 更新并重启
```

---

## 手动部署（不用 Docker）

### 环境要求

- Python 3.12+
- 预构建的 ChromaDB 知识库（`chroma_db/` 目录）

### 步骤

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 WORKTOOL_ROBOT_ID

# 3. 启动服务器
python3 app.py
```

### 使用 Gunicorn（生产环境）

```bash
pip install gunicorn
gunicorn app:app -b 0.0.0.0:5000 -w 2 --access-logfile -
```

---

## 配置说明

所有配置通过环境变量（`.env` 文件）管理：

| 变量 | 必需 | 说明 | 默认值 |
|------|------|------|--------|
| `WORKTOOL_ROBOT_ID` | **是** | WorkTool 机器人 ID | — |
| `WORKTOOL_API_URL` | 否 | WorkTool API 地址 | 官方 API |
| `CHROMA_DB_PATH` | 否 | 向量数据库路径 | `./chroma_db` |
| `CHROMA_COLLECTION` | 否 | Collection 名称 | `ifa_licensing_kb` |
| `NGROK_AUTH_TOKEN` | 推荐 | ngrok 认证令牌 | — |
| `FLASK_PORT` | 否 | 监听端口 | `5000` |
| `SUBMIT_EMAIL` | 否 | 资料提交邮箱 | `license@example.com` |
| `A1_FORM_URL` | 否 | A1 表格链接 | 语雀 PDF |

---

## 项目结构

```
ifa_knowledge_base/
├── app.py                 # 主程序（Flask 回调 + RAG + 状态机）
├── deploy.sh              # 一键部署脚本
├── docker-compose.yml     # Docker 编排
├── Dockerfile             # Docker 镜像
├── .env.example           # 配置模板
├── requirements.txt       # Python 依赖
├── chroma_db/             # 预构建向量知识库
├── Agent5-Lili_cleaned.md # 知识源文档
└── ifa_*.py               # 功能脚本（欢迎流程/资料推送/邮箱/培训等）
```

---

## 架构

```
群里 @Lili 提问
      ↓
  WorkTool 机器人
      ↓
  ngrok 隧道 (内网穿透)
      ↓
  Flask 回调服务器 (:5000)
      ├── 功能一：上牌申请识别 → 欢迎语
      ├── 功能二：上牌指引（有牌/无牌）
      └── 功能六：RAG 知识库检索 → 生成回复
            ↓
  WorkTool API 发消息 → 回复到群里
```

---

## 故障排查

### 服务启动失败

```bash
./deploy.sh logs    # 查看错误日志
```

常见原因：
- `.env` 中 `WORKTOOL_ROBOT_ID` 未配置
- `chroma_db/` 目录不存在

### 消息发不出去

- 检查 WorkTool 后台 AI 引擎类型是否为 **OpenClaw**
- 检查回调地址是否可达（ngrok 是否在运行）
- 确认 Robot 在 WTApp 中**在线**

### ngrok 地址变化

免费版 ngrok 每次重启地址会变，需要更新 WorkTool 后台的 AI 引擎 Base URL。

查询当前地址：
```bash
curl -s http://localhost:4040/api/tunnels | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['tunnels'][0]['public_url'])"
```

---

## 更新知识库

如果源文档有更新，重建向量数据库：

```bash
python3.12 rebuild_kb_v2.py
```

然后重新构建 Docker 镜像：

```bash
./deploy.sh update
```

---

## 技术栈

- **Web 框架**: Flask
- **向量数据库**: ChromaDB
- **Embedding 模型**: paraphrase-multilingual-MiniLM-L12-v2
- **容器化**: Docker + Docker Compose
- **内网穿透**: ngrok
