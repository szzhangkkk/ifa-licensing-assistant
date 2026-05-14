#!/usr/bin/env python3
"""
IFA 上牌指引推送脚本（功能2）
推送上牌流程文档至 IFA 群

触发方式：
  1. 运营手动触发（现在已实现）
  2. 新顾问进群后自动触发（等消息入口配置后）
  3. 定时推送（等 cronjob 配置后）

话术逻辑：
  Step 1: 发送「主动询问-1」→ 问顾问是否在其他地方上过牌
  Step 2a: 若顾问回复「有牌」→ 发「资料-3」
  Step 2b: 若顾问回复「无牌」→ 发「资料-1」+「资料-2」+「资料-3」+ A1表格
"""

import json
from datetime import datetime

# ─────────────────────────────────────────────
# 话术模板（严格按文档原文，不改写）
# ─────────────────────────────────────────────

A1_FORM_URL = "https://www.yuque.com/attachments/yuque/0/2026/pdf/28748258/1776425817432-dc71d778-7c33-409f-92f7-f1c690e5cea8.pdf"
A1_GUIDE_URL = "https://www.yuque.com/attachments/yuque/0/2026/pdf/28748258/1776425831092-a66816a2-c96d-4698-95ae-8d29f9b41061.pdf"

MESSAGES_STEP1 = [
    {
        "id": "主动询问-1",
        "content": (
            "请问您之前有在其他地方上过牌吗？"
        )
    }
]

MESSAGES_NEW_AGENT = [
    {
        "id": "资料-1",
        "content": (
            "上牌所需資料：\n\n"
            "1.HKID\n"
            "2.HK Address Proof\n"
            "3.銀行賬戶证明（如月结单）\n"
            "4.毕业证书\n"
            "5.学位证书\n"
            "6.内地院校毕业需学信网学历认证报告\n"
            "7.IIQE (Paper 1, 2, 3, 5), 視乎上什麼牌而定\n"
            "8.对上一年CPD記錄（如有）\n"
            "9.非永居需要護照\n"
            "10.非永居需要Visa\n"
            "11.学生签证需另外提供NOL（入境处出具的学生签证批准函）\n\n"
            "注意：A1表格中地址、手機號必須爲香港"
        )
    },
    {
        "id": "资料-2",
        "content": (
            "以上资料准备好后，请发送到邮箱：license@example.com\n"
            "邮件主题：Request for IA license registration-(英文名字)"
        )
    },
    {
        "id": "资料-3",
        "content": (
            "以上是上牌所需准备的资料，您可以提前先准备下，准备完成后发送指定邮箱即可"
        )
    },
    {
        "id": "A1表格",
        "content": (
            f"A1表格与填写指引：\n"
            f"📄 A1表格：（AWM）Form_A1_TC_Jan_2022.pdf\n"
            f"{A1_FORM_URL}\n\n"
            f"📄 签署指引：（AWM）簽署指引-Form_A1_TC_Jan_2022.pdf\n"
            f"{A1_GUIDE_URL}"
        )
    }
]

MESSAGES_EXISTING_AGENT = [
    {
        "id": "资料-3",
        "content": (
            "以上是上牌所需准备的资料，您可以提前先准备下，准备完成后发送指定邮箱即可"
        )
    }
]

# ─────────────────────────────────────────────
# 发送函数（调用 Hermes send_message）
# ─────────────────────────────────────────────

def send_to_ifa_group(message: str) -> dict:
    """发送消息到 IFA 群（占位函数，发送通道打通后实现）"""
    print(f"[TODO] send_to_ifa_group: {message[:50]}...")
    return {"status": "pending"}


def push_step1() -> list:
    """推送 Step1：主动询问是否上过牌"""
    print("\n" + "="*60)
    print("【功能2-Step1】发送主动询问：请问您之前有在其他地方上过牌吗？")
    print("="*60)
    sent = []
    for m in MESSAGES_STEP1:
        print(f"\n[{m['id']}]")
        print(m['content'])
        # TODO: 实际发送时取消注释
        # send_to_ifa_group(m['content'])
        sent.append(m)
    return sent


def push_new_agent_package() -> list:
    """推送完整新顾问上牌资料包"""
    print("\n" + "="*60)
    print("【功能2-新顾问】发送完整上牌资料包（未上过牌）")
    print("="*60)
    sent = []
    for m in MESSAGES_NEW_AGENT:
        print(f"\n[{m['id']}]")
        print(m['content'][:100] + "..." if len(m['content']) > 100 else m['content'])
        # TODO: 实际发送时取消注释
        # send_to_ifa_group(m['content'])
        sent.append(m)
    return sent


def push_existing_agent_package() -> list:
    """推送有牌顾问资料包（只发资料-3）"""
    print("\n" + "="*60)
    print("【功能2-有牌顾问】发送简化资料包（已上过牌）")
    print("="*60)
    sent = []
    for m in MESSAGES_EXISTING_AGENT:
        print(f"\n[{m['id']}]")
        print(m['content'])
        # TODO: 实际发送时取消注释
        # send_to_ifa_group(m['content'])
        sent.append(m)
    return sent


# ─────────────────────────────────────────────
# CLI 入口
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("IFA 上牌指引推送工具")
        print("用法:")
        print("  python ifa_doc_push.py step1        # 发送主动询问")
        print("  python ifa_doc_push.py new          # 发送新顾问完整资料包")
        print("  python ifa_doc_push.py existing     # 发送有牌顾问资料包")
        print("  python ifa_doc_push.py all-new      # 发送 step1 + 新顾问资料包")
        print("  python ifa_doc_push.py all-existing # 发送 step1 + 有牌顾问资料包")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "step1":
        push_step1()
    elif cmd == "new":
        push_new_agent_package()
    elif cmd == "existing":
        push_existing_agent_package()
    elif cmd == "all-new":
        push_step1()
        push_new_agent_package()
    elif cmd == "all-existing":
        push_step1()
        push_existing_agent_package()
    else:
        print(f"未知命令: {cmd}")
        sys.exit(1)
