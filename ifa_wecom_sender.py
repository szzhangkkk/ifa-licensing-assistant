#!/usr/bin/env python3
"""
IFA WeCom 群消息发送客户端
通过 WorkTool API 发送群消息

API 格式：
  POST https://api.worktool.ymdyes.cn/wework/sendRawMessage
  Header: robotId=<robot_id>
  Body: {"socketType":2,"list":[{"type":203,"titleList":["<群名>"],"receivedContent":"<文本>","atList":[]}]}
"""

import json
import urllib.request
import urllib.error
import time
import os

# ─────────────────────────────────────────────
# WorkTool 配置
# ─────────────────────────────────────────────

WORKTOOL_API_URL = "https://api.worktool.ymdyes.cn/wework/sendRawMessage"
ROBOT_ID = os.environ.get("WORKTOOL_ROBOT_ID", "")  # 从环境变量读取


def send_text_to_group(text: str, group_name: str, robot_id: str = None) -> dict:
    """
    发送文本消息到 WorkTool 群

    Args:
        text: 要发送的文本内容
        group_name: 群名称（必须是机器人在的群）
        robot_id: 不传则使用默认的 ROBOT_ID
    """
    rid = robot_id or ROBOT_ID
    payload = {
        "socketType": 2,
        "list": [
            {
                "type": 203,
                "titleList": [group_name],
                "receivedContent": text,
                "atList": []
            }
        ]
    }

    url = f"{WORKTOOL_API_URL}?robotId={rid}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return {"success": result.get("code") == 0, "response": result}
    except urllib.error.URLError as e:
        return {"success": False, "error": str(e)}


def send_messages_to_group(messages: list[str], group_name: str, robot_id: str = None) -> list[dict]:
    """
    批量发送多条消息到群（逐条发送，有延迟）
    """
    results = []
    for msg in messages:
        result = send_text_to_group(msg, group_name, robot_id)
        results.append(result)
        status = "✅" if result.get("success") else "❌"
        print(f"  {status} {msg[:40]}...")
        time.sleep(1)  # QPM限制60，避免发太快
    return results


# ─────────────────────────────────────────────
# CLI 测试入口
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("WeCom 群消息发送工具")
        print("用法:")
        print("  python ifa_wecom_sender.py <群名> <文本>   # 发送单条")
        print("  python ifa_wecom_sender.py test             # 发送测试消息")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "test":
        group = sys.argv[2] if len(sys.argv) > 2 else "test群"
        result = send_text_to_group("✅ Lili 机器人连接测试成功！", group)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        group = cmd
        text = sys.argv[2] if len(sys.argv) > 2 else "测试消息"
        result = send_text_to_group(text, group)
        print(json.dumps(result, ensure_ascii=False, indent=2))
