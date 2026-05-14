#!/usr/bin/env python3
"""
IFA 进群欢迎流程 (功能1)
===============================
监听群消息中的「上牌申请」块 → 提取顾问信息 → 存记忆 → 发送欢迎语

触发条件：群里有「上牌申请」字样且包含 details/折叠块格式
"""

import re
import json
from datetime import datetime

# ============================================================
# 【核心1】消息解析 — 提取上牌申请信息
# ============================================================

# 文档里的格式是飞书导出的 details 折叠块
# 结构：
#   <details class="lake-collapse">
#     <summary>...标题...</summary>
#     <p>姓名：黃久運<br />最高学历：毅進文憑<br />...</p>
#   </details>

DETAILS_PATTERN = re.compile(
    r'<details\s+class="lake-collapse"[^>]*>(.*?)</details>',
    re.DOTALL
)
SUMMARY_PATTERN = re.compile(r'<summary[^>]*>(.*?)</summary>', re.DOTALL)
HTML_TAG_PATTERN = re.compile(r'<[^>]+>')
BR_PATTERN = re.compile(r'<br\s*/?>')
WHITESPACE_PATTERN = re.compile(r' {2,}')   # 只合并多余空格，不吞换行符

# 文档里「上牌申请」块的标题
APPLICATION_BLOCK_TITLE = "上牌申请"


def extract_html_details(text: str) -> list[dict]:
    """
    从飞书导出的 HTML 文本中提取所有 details 折叠块。
    返回：[{"title": "块标题", "content": "纯文本内容"}, ...]
    """
    results = []
    for m in DETAILS_PATTERN.finditer(text):
        inner = m.group(1)
        sm = SUMMARY_PATTERN.search(inner)
        title = HTML_TAG_PATTERN.sub('', sm.group(1) if sm else '').strip()
        content = BR_PATTERN.sub('\n', inner)
        content = HTML_TAG_PATTERN.sub('', content)
        content = WHITESPACE_PATTERN.sub(' ', content).strip()
        results.append({"title": title, "content": content})
    return results


def clean_field_line(line: str) -> str:
    """清洗「字段名：值」行，返回干净的值"""
    line = line.strip()
    # 去掉末尾的<br>残留
    line = BR_PATTERN.sub('', line)
    line = HTML_TAG_PATTERN.sub('', line)
    line = WHITESPACE_PATTERN.sub(' ', line).strip()
    return line


def parse_application_block(content: str) -> dict:
    """
    解析「上牌申请」块的内容，提取顾问档案字段。
    文档格式示例：
        上牌申请
        姓名：  黃久運
        最高学历：毅進文憑
        过往工作经历：財務策劃
        ...
    """
    lines = content.split('\n')
    record = {
        "姓名": None,
        "最高学历": None,
        "过往工作经历": None,
        "核心优势/资源": None,
        "保监局考试是否通过": None,
        "牌照号（如有）": None,
        "推荐人": None,
        "直属上级": None,
        "拟任职级": None,
        "原始文本": content,
    }

    for raw_line in lines:
        line = raw_line.strip()
        # 跳过空行
        if not line:
            continue
        # 跳过「上牌申请」本身那一行（summary标签里的文字残留）
        # 精确判断：整行==上牌申请，或者只有"上牌申请"一个字
        if line == "上牌申请":
            continue
        # 匹配「字段名：值」或「字段名 值」
        # 字段名可以是中文/英文
        match = re.match(r'^([^\s：:]+)[\s：:]+(.+)$', line)
        if match:
            key = match.group(1).strip()
            raw_val = match.group(2).strip()
            # 如果val里还有冒号，说明key被正则错误截断（如「核心优势 / 资源：xxx」）
            # 需要用冒号重新分割：key取"核心优势 + 冒号前"，val取冒号后
            colon_in_val = None
            for i, c in enumerate(raw_val):
                if c in '：:：':
                    colon_in_val = i
                    break
            if colon_in_val is not None:
                key = (key + raw_val[:colon_in_val]).strip()
                val = raw_val[colon_in_val + 1:].strip()
            else:
                val = raw_val
        else:
            # 正则分割失败时，用冒号位置手动分割（处理「核心优势 / 资源：xxx」等复杂key）
            colon_pos = None
            for i, c in enumerate(line):
                if c in '：:：':
                    colon_pos = i
                    break
            if colon_pos is None:
                continue
            key = line[:colon_pos].strip()
            val = line[colon_pos + 1:].strip()
            if not key or not val:
                continue

        if key in record:
            record[key] = val
        elif "学历" in key:
            record["最高学历"] = val
        elif "经历" in key:
            record["过往工作经历"] = val
        elif "核心优势" in key:
            record["核心优势/资源"] = val
        elif "考试" in key:
            record["保监局考试是否通过"] = val
        elif "牌照号" in key:
            record["牌照号（如有）"] = val
        elif "推荐人" in key:
            record["推荐人"] = val
        elif "直属上级" in key:
            record["直属上级"] = val
        elif "职级" in key:
            record["拟任职级"] = val

    return record


def extract_advisor_from_message(raw_text: str) -> dict | None:
    """
    入口函数：输入原始群消息文本，返回顾问档案或 None。
    """
    # 1. 提取所有 details 块
    blocks = extract_html_details(raw_text)

    # 2. 找「上牌申请」标题的块
    for block in blocks:
        if block["title"] == APPLICATION_BLOCK_TITLE:
            record = parse_application_block(block["content"])
            # 基本校验：至少有姓名
            if record.get("姓名"):
                return record

    return None


# ============================================================
# 【核心2】记忆存储 — 顾问档案写入 memory
# ============================================================

MEMORY_KEY = "ifa_advisor_pending"   # 待引导的顾问列表（还未完成进群流程）


def build_advisor_memory(record: dict) -> dict:
    """把提取到的顾问档案构建成 memory 格式"""
    return {
        "name": record.get("姓名"),
        "has_prior_license": None,       # 待询问确认
        "license_number": record.get("牌照号（如有）"),
        "education": record.get("最高学历"),
        "work_experience": record.get("过往工作经历"),
        "strengths": record.get("核心优势/资源"),
        "exam_passed": record.get("保监局考试是否通过"),
        "referrer": record.get("推荐人"),
        "direct_manager": record.get("直属上级"),
        "intended_level": record.get("拟任职级"),
        "join_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "phase": "pending_welcome_reply",  # 当前阶段：等待回复是否上过牌
        "raw_record": record,
    }


# ============================================================
# 【核心3】话术模板 — 欢迎语定义
# ============================================================

WELCOME_MSG_1 = """嘿！AWM的新星，欢迎您的到来！🌟

阳光明媚，因您而至。从今天起，您的职业旅程将翻开崭新的一页，我们无比期待与您携手同行。

为了让您无缝融入、从容启航，我们已为您准备了周全的入职支持体系：

🧑‍🏫 专属入职引导
📚 系统培训课程
🛠 全方位资源支持

愿您在AWM的每一天：
✨ 工作顺心，事业有成
🚀 成长可见，未来可期
🤝 团队共进，温暖同行"""

WELCOME_MSG_2 = """您好，这是为您建立的专属服务群，我是您的上牌小助手Lili，后续将由我来协助您完成上牌~"""

FOLLOW_UP_QUESTION = """请问您之前有在其他地方上过牌吗？"""


def format_welcome_messages(advisor_name: str = None) -> tuple[str, str, str]:
    """
    返回 (欢迎语1, 欢迎语2, 跟进问题)
    advisor_name 暂时没用——文档里的欢迎语是通用模板，不含姓名
    （如果要个性化，可在姓名后加"黃总"等）
    """
    return WELCOME_MSG_1, WELCOME_MSG_2, FOLLOW_UP_QUESTION


# ============================================================
# 【核心4】组装 — 主流程函数
# ============================================================

def process_new_advisor(raw_message_text: str) -> dict:
    """
    完整流程：
    1. 解析顾问信息
    2. 构建 memory 档案
    3. 返回要发送的消息内容

    返回 dict：
      {
        "success": bool,
        "advisor_record": dict,     # 顾问档案
        "welcome_msg_1": str,
        "welcome_msg_2": str,
        "follow_up_question": str,
        "memory_data": dict,        # 待写入 memory 的内容
        "error": str,               # 如果 success=False
      }
    """
    # Step 1: 提取顾问信息
    record = extract_advisor_from_message(raw_message_text)
    if not record:
        return {
            "success": False,
            "error": "未检测到「上牌申请」信息块，请确认消息格式是否包含 details 折叠块。"
        }

    # Step 2: 构建 memory 档案
    memory_data = build_advisor_memory(record)

    # Step 3: 取出话术
    w1, w2, fq = format_welcome_messages(record.get("姓名"))

    return {
        "success": True,
        "advisor_record": record,
        "welcome_msg_1": w1,
        "welcome_msg_2": w2,
        "follow_up_question": fq,
        "memory_data": memory_data,
    }


# ============================================================
# 【测试】手动传入文档里的示例消息，验证能正确解析
# ============================================================

SAMPLE_APPLICATION_BLOCK = """
<details class="lake-collapse">
<summary id="u93677bcd"><span class="ne-text">上牌申请</span></summary>
<p id="u12e41633" class="ne-p"><span class="ne-text"> 上牌申请<br /><br /></span><span class="ne-text">姓名：  黃久運<br /></span><span class="ne-text">最高学历：毅進文憑<br /></span><span class="ne-text">过往工作经历：財務策劃<br /></span><span class="ne-text">核心优势 / 资源：香港本地资源及客户资源优势<br /><br /><br /></span><span class="ne-text">保监局考试是否通过：通過<br /></span><span class="ne-text">牌照号（如有）： JB5346<br /><br /></span><span class="ne-text">团队归属↓<br /></span><span class="ne-text">推荐人：孫羽<br /></span><span class="ne-text">直属上级：孫羽<br /></span><span class="ne-text">拟任职级：AD(助理总监)  </span></p>
</details>
"""


if __name__ == "__main__":
    result = process_new_advisor(SAMPLE_APPLICATION_BLOCK)
    print("=" * 60)
    print("解析结果:")
    print("=" * 60)
    if result["success"]:
        print(f"✅ 成功提取顾问：{result['advisor_record'].get('姓名')}")
        print(f"   推荐人：{result['advisor_record'].get('推荐人')}")
        print(f"   直属上级：{result['advisor_record'].get('直属上级')}")
        print(f"   拟任职级：{result['advisor_record'].get('拟任职级')}")
        print(f"   考试通过：{result['advisor_record'].get('保监局考试是否通过')}")
        print()
        print("【欢迎语-1】")
        print(result["welcome_msg_1"])
        print()
        print("【欢迎语-2】")
        print(result["welcome_msg_2"])
        print()
        print("【跟进问题】")
        print(result["follow_up_question"])
    else:
        print(f"❌ 失败：{result['error']}")
