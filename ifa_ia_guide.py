#!/usr/bin/env python3
"""
IFA IA系统指引推送脚本（功能3）
运营同事手动触发，Agent 发送 IA 指引、TR协议、缴费通知等

触发方式：
  运营在群里@Lili 说「请发送IA指引」，或「请发送TR协议」等

话术（严格按文档原文，不改写）：
"""

# ─────────────────────────────────────────────
# IA系统指引
# ─────────────────────────────────────────────

IA_GUIDE_NEW_ACCOUNT = """@【客户姓名】，您的IA账号已建立完成，密码、操作指南、填写注意事项及需上传的资料都已发送至您的邮箱。

 因 A1 表格中包含我们协助修改与完善的内容，请完全按照A1申请表尽快完成线上资料填写哈~

[图片]

请先找到此邮件，点击<按此>启动账户，密码已以图片的形式发送至您的邮箱"""

IA_GUIDE_EXISTING_ACCOUNT = """@【客户姓名】，您的邮箱目前应该收到了三封邮件，请先删除之前创建账户的邮件后再进行新IA账户的启动及线上申请的填写哈

邮件1：删除之前创建账户的邮件
邮件2：IA推送的启动账户邮件
邮件3：操作指引"""

# ─────────────────────────────────────────────
# TR协议
# ─────────────────────────────────────────────

TR_AGREEMENT_SEND = """@【客户姓名】，TR 协议已发送至您的邮箱，请在签署前核对个人信息；确认无误后，于右下角签名栏签署即可（日期无需填写，将由同事完善）。

此外，请将『协议打印一式两份』签署完成后寄回香港，邮寄地址如下：

Brian Wong Pok Hong
+852 27233200
28th Floor of No.8 Wyndham
Street,Central,Hong Kong
中环云咸街8号28楼全层

完成后，请将快递单号及电子版协议提供给我一份哈~"""

TR_AGREEMENT_CONFIRMED = """@【客户姓名】，已盖章的电子版TR协议已发送至您的邮箱，请注意查收哈~"""

# ─────────────────────────────────────────────
# 交互沟通
# ─────────────────────────────────────────────

INTERACTION_FOLLOW_UP = """收到，两份协议正本寄出后，麻烦将快递单号提供给我下哈"""

# ─────────────────────────────────────────────
# 缴费
# ─────────────────────────────────────────────

PAYMENT_READY = """@【客户姓名】，您可以登录IA账户进行缴费了哈，完成后麻烦在群里和我同步下"""

# ─────────────────────────────────────────────
# 等待保监审核
# ─────────────────────────────────────────────

PENDING_INSPECTOR = """好的，您的申请目前已递交保监审批了哈，后续无论是审批通过还是被退回修改，您都会第一时间收到邮件通知，麻烦到时候和我同步下"""

# ─────────────────────────────────────────────
# 牌照吊销
# ─────────────────────────────────────────────

LICENSE_SUSPENDED = """@【客户姓名】💐🌈【客户姓名】，你当前持有的【个人保险代理】牌照处于暂时吊销的状态，若要申请【业务代表（经纪）】牌照，需先对原牌照进行撤销操作。

相关操作明细已邮件发送给您了，请注意查收哈~"""

# ─────────────────────────────────────────────
# 交互示例
# ─────────────────────────────────────────────

EXAMPLE_INTERACTION = """收到，两份协议正本寄出后，麻烦将快递单号提供给我下哈"""


# ─────────────────────────────────────────────
# CLI 入口
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("IFA IA指引推送工具（功能3）")
        print("用法:")
        print("  python ifa_ia_guide.py ia_new          # IA账户新建立通知")
        print("  python ifa_ia_guide.py ia_existing      # IA邮箱已有旧账户")
        print("  python ifa_ia_guide.py tr_send          # 发送TR协议待签署")
        print("  python ifa_ia_guide.py tr_confirmed     # TR协议签署完成确认")
        print("  python ifa_ia_guide.py payment          # 通知可缴费")
        print("  python ifa_ia_guide.py pending          # 等待保监审核")
        print("  python ifa_ia_guide.py suspended        # 牌照吊销通知")
        sys.exit(1)

    cmd = sys.argv[1]

    messages = {
        "ia_new":       ("IA系统指引-1（新建账户）", IA_GUIDE_NEW_ACCOUNT),
        "ia_existing":  ("IA系统指引邮件-2（有旧账户）", IA_GUIDE_EXISTING_ACCOUNT),
        "tr_send":      ("TR协议邮件-1（待签署）", TR_AGREEMENT_SEND),
        "tr_confirmed": ("TR协议邮件-2（已签署）", TR_AGREEMENT_CONFIRMED),
        "payment":      ("缴费通知", PAYMENT_READY),
        "pending":      ("等待保监审核", PENDING_INSPECTOR),
        "suspended":    ("牌照吊销通知", LICENSE_SUSPENDED),
    }

    if cmd in messages:
        title, content = messages[cmd]
        print(f"\n{'='*60}")
        print(f"【功能3】{title}")
        print(f"{'='*60}")
        print(content)
    else:
        print(f"未知命令: {cmd}")
        sys.exit(1)
