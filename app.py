#!/usr/bin/env python3
"""
IFA 上牌小助手 (Lili Bot) — 主程序
=====================================
统一入口：Flask 回调服务器 + RAG 知识库 + 状态机问答

功能：
  功能一 — 进群欢迎 + 上牌申请识别
  功能二 — 上牌指引（有牌/无牌 分支）
  功能六 — RAG 知识库问答

部署方式：
  1. Docker (推荐)      → docker compose up -d
  2. 直接运行             → pip install -r requirements.txt && python app.py
  3. 生产环境             → gunicorn app:app -b 0.0.0.0:5000

依赖：Python 3.12+, ChromaDB 已构建
"""

import os
import sys
import json
import logging
from datetime import datetime

# ── 可选依赖：在需要时才导入 ──
try:
    from flask import Flask, request, jsonify
except ImportError:
    print("[错误] 缺少 flask，请运行: pip install -r requirements.txt")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("[错误] 缺少 requests，请运行: pip install -r requirements.txt")
    sys.exit(1)

# ── 日志 ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("lili-bot")

# ============================================================
# 配置 — 全部从环境变量读取，有合理默认值
# ============================================================

ROBOT_ID = os.environ.get("WORKTOOL_ROBOT_ID", "")
WORKTOOL_API = os.environ.get(
    "WORKTOOL_API_URL",
    "https://api.worktool.ymdyes.cn/wework/sendRawMessage",
)
# 向量数据库配置（Milvus 优先，ChromaDB 降级备选）
MILVUS_DB_PATH = os.environ.get("MILVUS_DB_PATH", "./milvus.db")
CHROMA_PATH = os.environ.get("CHROMA_DB_PATH", "./chroma_db")
CHROMA_COLLECTION = os.environ.get("CHROMA_COLLECTION", "ifa_licensing_kb")
MILVUS_COLLECTION = os.environ.get("MILVUS_COLLECTION", "ifa_licensing_kb")
FLASK_PORT = int(os.environ.get("FLASK_PORT", "5000"))
FLASK_HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
A1_FORM_URL = os.environ.get("A1_FORM_URL", "")
A1_GUIDE_URL = os.environ.get("A1_GUIDE_URL", "")
SUBMIT_EMAIL = os.environ.get("SUBMIT_EMAIL", "license@example.com")

app = Flask(__name__)

# ============================================================
# 工具函数
# ============================================================

# 等待回复状态文件（Docker 容器内用 /tmp）
PENDING_FILE = "/tmp/ifa_pending_license_reply.txt"


def save_pending(name, group):
    """记录正在等待回复的顾问"""
    with open(PENDING_FILE, "w") as f:
        f.write(f"{name}|{group}")
    logger.info(f"[状态] 等待 {name}@{group} 回复是否上过牌")


def read_pending():
    """读取等待回复的顾问信息"""
    if not os.path.exists(PENDING_FILE):
        return None, None
    with open(PENDING_FILE) as f:
        content = f.read().strip()
    if not content:
        return None, None
    parts = content.split("|", 1)
    return parts[0], parts[1] if len(parts) > 1 else ""


def clear_pending():
    """清除等待状态"""
    if os.path.exists(PENDING_FILE):
        os.remove(PENDING_FILE)


# ============================================================
# RAG 检索引擎（Milvus 优先，ChromaDB 懒加载降级）
# ============================================================

class RAGEngine:
    """向量检索引擎 — 启动时预加载模型和 Milvus，ChromaDB 仅降级时导入"""

    # 内部文档关键词（不对外暴露的模板和流程描述）
    # 原则: 只过滤 Bot 自身配置/流程描述/占位符，不误杀面向用户的知识
    # "## " / "功能" / "上牌申请" 已移除 — 太宽泛，会误杀正常知识
    _INTERNAL = [
        # Bot 自描述 / 占位符
        "Agent", "上牌小助手", "【例：", "```plain",
        # 内部流程标记
        "触发条件", "核心流程", "【主动推送】", "【被动问答】",
        # 内部操作指令（非用户知识）
        "资料-", "欢迎语", "等待保监",
    ]

    def __init__(self, milvus_path, milvus_collection,
                 chroma_path, chroma_collection):
        self.milvus_path = milvus_path
        self.milvus_collection = milvus_collection
        self.chroma_path = chroma_path
        self.chroma_collection = chroma_collection
        self._milvus = None        # MilvusClient | None
        self._model = None         # SentenceTransformer | None
        self._using = None         # "milvus" | "chromadb" | None

    # ── 属性 ──

    @property
    def status(self) -> str:
        """当前使用的向量数据库"""
        return self._using or "none"

    @property
    def db_exists(self) -> bool:
        return os.path.exists(self.milvus_path) or os.path.exists(self.chroma_path)

    # ── 启动预热 ──

    def warmup(self):
        """启动时预加载 embedding 模型和 Milvus 连接（阻塞，~10-30 秒）"""
        logger.info("[RAG] 预热中...")
        self._load_model()
        self._load_milvus()
        if self._using == "milvus":
            logger.info(f"[RAG] 就绪 — Milvus ({self.milvus_path})")
        elif self._using == "chromadb":
            logger.info(f"[RAG] 就绪 — ChromaDB 降级 ({self.chroma_path})")
        else:
            logger.warning("[RAG] 未找到任何向量数据库")

    def _load_model(self):
        """加载 embedding 模型（470MB，仅一次）"""
        if self._model is not None:
            return
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        from sentence_transformers import SentenceTransformer
        logger.info("[RAG] 加载 embedding 模型 paraphrase-multilingual-MiniLM-L12-v2 ...")
        self._model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        logger.info("[RAG] embedding 模型已就绪")

    def _load_milvus(self):
        """连接 Milvus"""
        if self._milvus is not None:
            return
        if not os.path.exists(self.milvus_path):
            logger.info(f"[RAG] Milvus 不存在，尝试 ChromaDB...")
            self._try_chromadb_on_startup()
            return
        try:
            from pymilvus import MilvusClient
            self._milvus = MilvusClient(self.milvus_path)
            if not self._milvus.has_collection(self.milvus_collection):
                logger.info(f"[RAG] Milvus collection 不存在")
                self._milvus.close()
                self._milvus = None
                self._try_chromadb_on_startup()
                return
            self._using = "milvus"
        except Exception as e:
            logger.warning(f"[RAG] Milvus 不可用: {e}")
            self._milvus = None
            self._try_chromadb_on_startup()

    def _try_chromadb_on_startup(self):
        """启动时尝试 ChromaDB（仅在 Milvus 不可用时）"""
        try:
            import chromadb
            if not os.path.exists(self.chroma_path):
                return
            c = chromadb.PersistentClient(path=self.chroma_path)
            c.get_collection(self.chroma_collection)
            self._using = "chromadb"
        except Exception:
            pass

    # ── 检索入口 ──

    def search(self, question: str) -> str | None:
        """检索知识库，返回匹配文本或 None"""
        if not question or not question.strip():
            return None
        if self._model is None:
            self._load_model()
        if self._model is None:  # 加载失败
            return None
        emb = self._model.encode([question], normalize_embeddings=True)[0].tolist()

        # Milvus 优先
        if self._milvus is not None:
            result = self._search_milvus(emb)
            if result:
                logger.info(f"[RAG] Milvus 命中: {result[:80]}...")
                return f"根据知识库信息：{result[:500]}"

        # ChromaDB 降级（用同一个 embedding，保证向量空间一致）
        result = self._search_chromadb(emb)
        if result:
            logger.info(f"[RAG] ChromaDB 降级命中: {result[:80]}...")
            return f"根据知识库信息：{result[:500]}"

        return None

    def _search_milvus(self, emb):
        """Milvus 向量检索 + 内部关键词过滤"""
        try:
            results = self._milvus.search(
                collection_name=self.milvus_collection,
                data=[emb],
                limit=10,  # 多取一些，防止 template 过滤后不够
                output_fields=["text", "chunk_type", "module"],
                filter='chunk_type == "text"',
            )
        except Exception as e:
            logger.error(f"[RAG] Milvus 检索异常: {e}")
            return None

        if not results or not results[0]:
            return None

        valid = []
        for hit in results[0]:
            text = (hit.get("entity", {}).get("text", "")).strip()
            if not text:
                continue
            ct = hit.get("entity", {}).get("chunk_type", "")
            if ct == "template":
                # template 双重过滤：类型标记 + 关键词
                if self._is_internal(text):
                    continue
                continue  # template 一律不对外
            # text 类型是正常知识内容，仅过滤内部文档标记
            if self._is_internal(text):
                continue
            valid.append(text)

        return "\n".join(valid[:2]) if valid else None

    def _search_chromadb(self, emb):
        """ChromaDB 降级检索 — 用统一 embedding 避免向量空间不一致"""
        try:
            import chromadb
        except ImportError:
            return None
        try:
            if not os.path.exists(self.chroma_path):
                return None
            client = chromadb.PersistentClient(path=self.chroma_path)
            collection = client.get_collection(self.chroma_collection)
            # 用 query_embeddings 而不是 query_texts
            # 保证和建库时同一个 MiniLM-L12 向量空间
            results = collection.query(
                query_embeddings=[emb],
                n_results=5,
                where={"chunk_type": {"$in": ["text"]}},
            )
            if not (results and results.get("documents") and results["documents"][0]):
                return None
            valid = [
                d for d in results["documents"][0]
                if d.strip() and not self._is_internal(d)
            ]
            return "\n".join(valid[:2]) if valid else None
        except Exception as e:
            logger.error(f"[RAG] ChromaDB 降级检索失败: {e}")
            return None

    @classmethod
    def _is_internal(cls, text: str) -> bool:
        return any(kw.lower() in text.lower() for kw in cls._INTERNAL)


# ── 全局引擎实例（在 __main__ 中 warmup）──
rag_engine: RAGEngine | None = None


# ============================================================
# WorkTool 消息发送
# ============================================================

def send_to_worktool(group_name: str, message: str, at_list=None):
    """通过 WorkTool API 发送消息到群"""
    if not ROBOT_ID:
        logger.error("[发送] 未配置 WORKTOOL_ROBOT_ID，无法发送消息")
        return None

    if at_list is None:
        at_list = []

    payload = {
        "socketType": 2,
        "list": [{
            "type": 203,
            "titleList": [group_name],
            "receivedContent": message,
            "atList": at_list,
        }],
    }

    try:
        resp = requests.post(
            WORKTOOL_API,
            params={"robotId": ROBOT_ID},
            json=payload,
            timeout=10,
        )
        logger.info(f"[发送] {resp.status_code} - {resp.text[:200]}")
        return resp.json()
    except Exception as e:
        logger.error(f"[发送] 失败: {e}")
        return None


# ============================================================
# 回复生成
# ============================================================

def generate_reply(question_orig: str):
    """根据问题生成回复，返回 str 或 None（不回复）

    优先级：
      1. 问候语 → 直接回复（人情世故不走 RAG）
      2. 感谢/确认 → 静默
      3. 结束对话 → 告别语
      4. RAG 检索 → 知识库优先于硬编码
      5. 意图检测 → 非上牌拒绝
      6. 关键词兜底 → 硬编码回复
    """
    q = question_orig.lower().strip()

    # ── 问候语 ──
    if any(k in q for k in ["你好", "hi", "hello", "在吗"]):
        return "你好！我是上牌小助手，有什么关于上牌的问题可以问我～"

    # ── 感谢/确认类：静默不回复 ──
    ack_keywords = [
        "好的谢谢", "好的，", "好谢谢", "好知道了", "了解", "知道了",
        "明白了", "嗯嗯", "嗯", "收到", "没问题", "好", "可以", "行",
        "好嘞", "谢谢", "感谢", "多谢", "thx", "thanks", "谢啦", "谢了",
    ]
    if any(k in q for k in ack_keywords):
        return None

    # ── 结束对话 ──
    end_keywords = [
        "没有其他问题了", "暂时没问题了", "暂时没有了", "没什么问题了",
        "没了", "没有了", "没问题了", "就这样", "就这样吧",
        "没有了谢谢", "没了谢谢",
    ]
    if any(k in question_orig for k in end_keywords):
        return "好的！祝您上牌顺利，如有需要随时联系我～\n再见！👋"

    # ── RAG 检索（优先于硬编码回复）──
    if rag_engine is not None:
        rag_result = rag_engine.search(question_orig)
    else:
        rag_result = None
    if rag_result:
        return rag_result

    # ── 意图检测：非上牌相关直接拒绝 ──
    license_keywords = [
        "上牌", "领牌", "牌照", "保险", "考试", "IIQE",
        "卷1", "卷2", "卷3", "卷4", "卷5",
        "保监", "经纪行", "材料", "学历", "推荐信", "cpd", "续牌",
        "投保", "理赔", "产品", "人寿", "一般保险", "长期保险",
        "年金", "旅游险", "中介人", "代理人", "IFA", "IA", "CPD",
        "保单", "要约", "核保", "受保", "受益人", "保费",
        "永居", "非永居", "身份证", "护照", "签证", "visa",
        "银行账户", "地址证明", "毕业证书", "学位证", "学历认证",
        "学信网", "考试合格证", "合格证", "成绩",
        # 通用询问
        "你好", "在吗", "帮忙", "请问", "咨询", "问一下", "问下",
        "有问题",
        # 确认/感谢类
        "好的", "好的谢谢", "了解", "知道了", "明白了", "嗯嗯",
        "谢谢", "感谢", "多谢",
    ]
    has_intent = any(k in question_orig for k in license_keywords)
    if not has_intent:
        return (
            "抱歉，我暂时没有理解您的问题。我是上牌小助手，"
            "主要协助上牌相关咨询。\n"
            "如有上牌材料、考试、流程等问题，欢迎随时问我～\n"
            "如需人工服务请私信。"
        )

    # ── 关键词兜底（RAG 未命中时的硬编码回复）──
    if any(k in q for k in ["上牌", "流程", "步骤"]):
        return (
            "上牌流程大致如下：\n"
            "1️⃣ 准备材料（身份证、学历证明、考试合格证等）\n"
            "2️⃣ 联系经纪行提交申请\n"
            "3️⃣ 等待审核（通常 5-10 个工作日）\n"
            "4️⃣ 审核通过后获取上牌结果\n\n"
            "如有具体问题，欢迎继续提问！"
        )

    if any(k in q for k in ["时间", "多久", "周期"]):
        return (
            "上牌审核周期一般为 5-10 个工作日，"
            "具体看经纪行和保险公司的处理速度。"
            "如有加急需求，可以联系经纪行沟通。"
        )

    if any(k in q for k in ["材料", "准备什么", "需要什么"]):
        return (
            "上牌一般需要准备：\n"
            "• 身份证\n"
            "• 学历证明\n"
            "• 保险从业资格考试合格证\n"
            "• 经纪行推荐信\n\n"
            "具体材料清单可以私信我获取～"
        )

    if any(k in q for k in ["驳回", "被拒", "失败"]):
        return (
            "材料驳回常见原因：\n"
            "• 学历证明信息不符\n"
            "• 考试合格证已过期\n"
            "• 推荐信格式不对\n\n"
            "建议核对材料后重新提交，或私信我帮你看看具体问题。"
        )

    return (
        "抱歉，这个问题我暂时没有准确答案，建议联系经纪行确认。\n"
        "也可以私信我，帮你转人工处理。"
    )


# ============================================================
# 回调入口
# ============================================================

@app.route("/worktool-callback", methods=["POST"])
def callback():
    """WorkTool 消息回调"""
    data = request.get_json(silent=True)
    if data is None:
        logger.warning("[回调] 无法解析 JSON")
        return jsonify({"code": 1, "message": "invalid json"})

    logger.info(f"[回调] {json.dumps(data, ensure_ascii=False)[:300]}")

    # ── 解析字段 ──
    spoken = data.get("spoken", "")
    raw_spoken = data.get("rawSpoken", "")
    received_name = data.get("receivedName", "未知")
    group_name = data.get("groupName", "") or data.get("groupRemark", "")
    at_me = str(data.get("atMe", False)).lower() == "true"
    text_type = data.get("textType", 1)

    # OpenClaw 备用字段
    content_oc = (
        data.get("content")
        or data.get("text")
        or data.get("message")
        or data.get("msg")
        or data.get("contentText")
        or ""
    )
    group_oc = (
        data.get("groupName")
        or data.get("group")
        or data.get("roomName")
        or data.get("chatName")
        or ""
    )
    user_oc = (
        data.get("userName")
        or data.get("user")
        or data.get("fromUser")
        or data.get("sender")
        or data.get("receivedName")
        or "未知"
    )

    # 判断消息来源格式
    if spoken or raw_spoken:
        question = spoken.strip() or raw_spoken.strip()
        parse_mode = "QA"
    elif content_oc:
        question = content_oc.strip()
        parse_mode = "OpenClaw"
        if not group_name:
            group_name = group_oc
        if received_name == "未知":
            received_name = user_oc
    else:
        logger.warning("[回调] 无法解析消息内容")
        return jsonify({"code": 0, "message": "empty message"})

    # 去掉 @me/@机器人 前缀
    for prefix in ["@me ", "@ME ", "@机器人 ", "[@机器人] "]:
        if question.startswith(prefix):
            question = question[len(prefix):].strip()
            break

    logger.info(
        f"[解析] 模式={parse_mode} 用户={received_name} "
        f"群={group_name} 内容={question[:50]}"
    )

    # ============================================================
    # 功能一：上牌申请识别 + 欢迎语
    # ============================================================
    if "上牌申请" in question and "姓名" in question:
        logger.info(f"[功能一] 检测到上牌申请，来自 {received_name}")

        # 提取姓名
        name = ""
        for line in question.split("\n"):
            if "姓名" in line and "：" in line:
                name = line.split("：")[-1].strip()
                break

        welcome1 = (
            "嘿！AWM的新星，欢迎您的到来！🌟\n\n"
            "阳光明媚，因您而至。从今天起，您的职业旅程将翻开崭新的一页，"
            "我们无比期待与您携手同行。\n\n"
            "为了让您无缝融入、从容启航，我们已为您准备了周全的入职支持体系：\n\n"
            "🧑‍🏫 专属入职引导\n"
            "📚 系统培训课程\n"
            "🛠 全方位资源支持\n\n"
            "愿您在AWM的每一天：\n"
            "✨ 工作顺心，事业有成\n"
            "🚀 成长可见，未来可期\n"
            "🤝 团队共进，温暖同行"
        )
        welcome2 = "您好，这是为您建立的专属服务群，我是您的上牌小助手Lili，后续将由我来协助您完成上牌~"
        ask1 = "请问您之前有在其他地方上过牌吗？"

        if group_name:
            send_to_worktool(group_name, welcome1)
            send_to_worktool(group_name, welcome2)
            at_text = (
                f"@{received_name} " + ask1
                if received_name != "未知"
                else ask1
            )
            send_to_worktool(group_name, at_text)
            save_pending(received_name, group_name)

        logger.info(f"[功能一] 已发送欢迎语给 {received_name}")
        return jsonify({"code": 0, "message": "success"})

    # ============================================================
    # 功能二：上牌指引（有牌/无牌 分支）
    # ============================================================
    pending_name, pending_group = read_pending()
    in_pending = (
        pending_name
        and pending_group
        and received_name == pending_name
        and group_name == pending_group
    )

    if in_pending:
        logger.info(f"[功能二] 收到 {pending_name} 的回复: {question}")

        # 判断
        no_license = any(k in question for k in [
            "没有上过牌", "没上牌", "没有上牌", "未曾上牌",
            "还没上牌", "未上牌", "没领牌", "没有领牌",
            "未曾领牌", "还没领牌",
            "没有在任何地方", "没有在其他地方", "未在任何地方",
        ])
        has_license = any(k in question for k in [
            "有牌", "已上牌", "已领牌", "有牌照", "已取得牌",
        ])
        has_ctx = any(k in question for k in ["上牌", "领牌", "牌照"])
        negation = "没有在" in question and has_ctx

        if no_license or negation:
            logger.info(f"[功能二] {pending_name} 没上过牌，发送资料清单")
            clear_pending()

            info1 = (
                "上牌所需资料：\n\n"
                "1. HKID\n"
                "2. HK Address Proof\n"
                "3. 银行账户证明（如月结单）\n"
                "4. 毕业证书\n"
                "5. 学位证书\n"
                "6. 内地院校毕业需学信网学历认证报告\n"
                "7. IIQE (Paper 1, 2, 3, 5)，视乎上什么牌而定\n"
                "8. 对上一年CPD记录（如有）\n"
                "9. 非永居需要护照\n"
                "10. 非永居需要Visa\n"
                "11. 学生签证需另外提供NOL（入境处出具的学生签证批准函）\n\n"
                "注意：A1表格中地址、手机号必须为香港"
            )
            # 使用环境变量中的邮箱
            email_addr = SUBMIT_EMAIL or "license@example.com"
            info2 = (
                f"以上资料准备好后，请发送到邮箱：{email_addr}\n"
                "邮件主题：Request for IA license registration-(英文名字)"
            )
            info3 = "以上是上牌所需准备的资料，您可以提前先准备下，准备完成后发送指定邮箱即可"

            send_to_worktool(group_name, info1)
            send_to_worktool(group_name, info2)
            send_to_worktool(group_name, info3)

            return jsonify({"code": 0, "message": "success"})

        elif has_license:
            logger.info(f"[功能二] {pending_name} 已上过牌，跳过")
            clear_pending()
            return jsonify({"code": 0, "message": "success"})

        else:
            logger.info(f"[功能二] {pending_name} 回复不确定，继续等待")
            return jsonify({"code": 0, "message": "success"})

    # 清理过期 pending
    if pending_name and not in_pending:
        clear_pending()

    # ============================================================
    # 功能六：RAG 知识库问答
    # ============================================================
    if question and len(question) > 0 and at_me:
        logger.info(f"[功能六] RAG 问答: {question[:50]}")
        reply = generate_reply(question)
        if reply and group_name:
            send_to_worktool(group_name, reply)
            logger.info(f"[回复] {reply[:80]}")
        elif reply is None:
            logger.info("[回复] 静默（感谢/确认类）")

    return jsonify({"code": 0, "message": "success"})


# ============================================================
# 健康检查
# ============================================================

@app.route("/health")
def health():
    """健康检查端点"""
    engine_status = rag_engine.status if rag_engine else "not_initialized"
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "vector_db": engine_status,
        "milvus_db": engine_status == "milvus",
        "chroma_db": engine_status == "chromadb",
        "robot_configured": bool(ROBOT_ID),
        "version": "1.2.0",
    })


@app.route("/")
def index():
    return jsonify({
        "name": "IFA 上牌小助手 (Lili Bot)",
        "version": "1.2.0",
        "vector_db": "Milvus Lite + ChromaDB fallback",
        "endpoints": {
            "callback": "/worktool-callback",
            "health": "/health",
        },
    })


# ============================================================
# 启动
# ============================================================

if __name__ == "__main__":
    print("=" * 55)
    print("  IFA 上牌小助手 (Lili Bot) v1.2.0")
    print("=" * 55)
    print(f"  监听地址 : http://{FLASK_HOST}:{FLASK_PORT}")
    print(f"  回调端点 : /worktool-callback")
    print(f"  健康检查 : /health")
    print(f"  Robot ID : {'已配置' if ROBOT_ID else '❌ 未配置!'}")

    # 初始化 RAG 引擎（预加载模型 + Milvus 连接）
    print("  向量数据库: 初始化中...")
    rag_engine = RAGEngine(
        MILVUS_DB_PATH, MILVUS_COLLECTION,
        CHROMA_PATH, CHROMA_COLLECTION,
    )
    rag_engine.warmup()
    print(f"  向量数据库: {rag_engine.status.upper()} ({'Milvus' if rag_engine.status == 'milvus' else 'ChromaDB' if rag_engine.status == 'chromadb' else '未找到'})")
    print("=" * 55)

    if not ROBOT_ID:
        print("\n⚠️  警告: WORKTOOL_ROBOT_ID 未设置!")
        print("  请设置环境变量或在 .env 文件中配置\n")

    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=False)
