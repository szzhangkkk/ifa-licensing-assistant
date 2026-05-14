#!/usr/bin/env python3
"""
IFA 合规培训提醒脚本（功能5）
开设邮箱后一天，提醒顾问进行合规培训

触发条件：
  运营手动触发，或定时任务自动触发

话术（严格按文档原文，不改写）：
"""

# ─────────────────────────────────────────────
# 合规培训-1：通用培训通知
# ─────────────────────────────────────────────

TRAINING_NOTIFICATION = """亲爱的同事们

应保监局要求，每位持牌代理人必需完成合规培训，确保行事符合监管要求，请您完成以下课程的观看，并完成签到表和培训评估。

📅 主题：合规培训
🕒 完成时间：【2026年4月22日前】
📍 地点：腾讯会议
🔗 课程链接：https://meeting.tencent.com/crm/NAjVLw0M4a
🔖 访问密码：ICA4

温馨提示：观看完成后需要完成签到表和培训评估签署，签署完成需返回给我们～

附件：
- Orientation Attendance Confirmation_vc(2).pdf
- Orientation Training Assessment_V2_简(2).pdf"""

# ─────────────────────────────────────────────
# 合规培训-2：@顾问个人提醒
# ─────────────────────────────────────────────

TRAINING_PERSONAL = """@【客户姓名】，以上是上牌完成后，必须学习的课程及需签署的文件，请务必在规定时间内尽快完成，完成后将电子版发送群中即可无需邮寄"""

# ─────────────────────────────────────────────
# CLI 入口
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("IFA 合规培训提醒工具（功能5）")
        print("用法:")
        print("  python ifa_training_reminder.py general   # 发送合规培训-1（通用通知）")
        print("  python ifa_training_reminder.py personal   # 发送合规培训-2（@顾问）")
        sys.exit(1)

    cmd = sys.argv[1]

    messages = {
        "general":  ("合规培训-1（通用通知）", TRAINING_NOTIFICATION),
        "personal": ("合规培训-2（@顾问）", TRAINING_PERSONAL),
    }

    if cmd in messages:
        title, content = messages[cmd]
        print(f"\n{'='*60}")
        print(f"【功能5】{title}")
        print(f"{'='*60}")
        print(content)
    else:
        print(f"未知命令: {cmd}")
        sys.exit(1)
