#!/usr/bin/env python3
"""
企业微信 AI Bot SDK 长连接 (WebSocket)
直接通过 WebSocket 连接 openws.work.weixin.qq.com，
使用 aibot_subscribe 协议认证，收发消息。

用法:
    python wecom_sdk_long_connection.py

配置: 修改下方 BOT_ID / SECRET
"""

import asyncio
import json
import logging
import uuid
import sys
import os

import aiohttp

# ============================================================
# 配置 - Bot 凭证（从环境变量读取，不硬编码）
# ============================================================
BOT_ID = os.environ.get("WECOM_BOT_ID", "")
SECRET = os.environ.get("WECOM_BOT_SECRET", "")

# WebSocket 网关地址
WS_URL = "wss://openws.work.weixin.qq.com"

# 心跳间隔 (秒)
HEARTBEAT_INTERVAL = 30

# 连接超时
CONNECT_TIMEOUT = 20

# ============================================================
# 日志
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("wecom-sdk")

# ============================================================
# 协议常量
# ============================================================
CMD_SUBSCRIBE = "aibot_subscribe"
CMD_CALLBACK = "aibot_msg_callback"
CMD_LEGACY_CALLBACK = "aibot_callback"
CMD_EVENT_CALLBACK = "aibot_event_callback"
CMD_SEND = "aibot_send_msg"
CMD_RESPONSE = "aibot_respond_msg"
CMD_PING = "ping"

CALLBACK_COMMANDS = {CMD_CALLBACK, CMD_LEGACY_CALLBACK}


def new_req_id(prefix: str = "req") -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


class WeComLongConnection:
    """企业微信 AI Bot WebSocket 长连接客户端"""

    def __init__(self, bot_id: str, secret: str, ws_url: str = WS_URL):
        self.bot_id = bot_id
        self.secret = secret
        self.ws_url = ws_url
        self.device_id = uuid.uuid4().hex

        self.session: aiohttp.ClientSession | None = None
        self.ws: aiohttp.ClientWebSocketResponse | None = None
        self.running = False
        self.pending_responses: dict[str, asyncio.Future] = {}

    # ----------------------------------------------------------
    # 连接管理
    # ----------------------------------------------------------

    async def connect(self) -> bool:
        """建立 WebSocket 连接并认证"""
        logger.info("正在连接 %s ...", self.ws_url)

        self.session = aiohttp.ClientSession(trust_env=True)

        try:
            self.ws = await asyncio.wait_for(
                self.session.ws_connect(
                    self.ws_url,
                    heartbeat=HEARTBEAT_INTERVAL * 2,
                ),
                timeout=CONNECT_TIMEOUT,
            )
        except Exception as e:
            logger.error("WebSocket 连接失败: %s", e)
            await self.session.close()
            return False

        logger.info("WebSocket 已连接，正在发送认证请求...")

        # 发送 aibot_subscribe 认证帧
        req_id = new_req_id("subscribe")
        await self.ws.send_json({
            "cmd": CMD_SUBSCRIBE,
            "headers": {"req_id": req_id},
            "body": {
                "bot_id": self.bot_id,
                "secret": self.secret,
                "device_id": self.device_id,
            },
        })
        logger.info("已发送 aibot_subscribe [req_id=%s]", req_id)

        # 等待认证应答
        try:
            deadline = asyncio.get_running_loop().time() + CONNECT_TIMEOUT
            while True:
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    raise TimeoutError("等待认证应答超时")

                msg = await asyncio.wait_for(self.ws.receive(), timeout=remaining)

                if msg.type == aiohttp.WSMsgType.TEXT:
                    payload = json.loads(msg.data)
                    logger.debug("收到帧: %s", json.dumps(payload, ensure_ascii=False)[:200])

                    # 跳过 ping
                    if payload.get("cmd") == CMD_PING:
                        continue

                    # 匹配 req_id
                    headers = payload.get("headers", {})
                    if headers.get("req_id") == req_id:
                        errcode = payload.get("body", {}).get("errcode", payload.get("errcode", 0))
                        errmsg = payload.get("body", {}).get("errmsg", payload.get("errmsg", "OK"))
                        if errcode not in (0, None):
                            logger.error("认证失败: errcode=%s errmsg=%s", errcode, errmsg)
                            return False
                        logger.info("✅ 认证成功! errcode=%s errmsg=%s", errcode, errmsg)
                        return True

                    logger.debug("忽略预认证帧: cmd=%s", payload.get("cmd"))

                elif msg.type in {aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.ERROR}:
                    raise RuntimeError("认证期间 WebSocket 关闭")

        except Exception as e:
            logger.error("认证失败: %s", e)
            return False

    async def disconnect(self):
        """断开连接"""
        self.running = False
        if self.ws and not self.ws.closed:
            await self.ws.close()
        if self.session and not self.session.closed:
            await self.session.close()
        logger.info("已断开连接")

    # ----------------------------------------------------------
    # 消息循环
    # ----------------------------------------------------------

    async def run(self):
        """主循环: 连接 → 监听消息 → 自动重连"""
        self.running = True

        # 连接
        if not await self.connect():
            logger.error("无法建立连接，退出")
            return

        # 启动心跳和消息监听
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        listen_task = asyncio.create_task(self._listen_loop())

        try:
            await asyncio.gather(heartbeat_task, listen_task)
        except asyncio.CancelledError:
            pass
        finally:
            await self.disconnect()

    async def _heartbeat_loop(self):
        """发送应用层 ping 保持连接"""
        try:
            while self.running:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                if not self.ws or self.ws.closed:
                    continue
                try:
                    await self.ws.send_json({
                        "cmd": CMD_PING,
                        "headers": {"req_id": new_req_id("ping")},
                        "body": {},
                    })
                    logger.debug("💓 ping")
                except Exception as e:
                    logger.warning("心跳发送失败: %s", e)
        except asyncio.CancelledError:
            pass

    async def _listen_loop(self):
        """监听 WebSocket 消息"""
        while self.running and self.ws and not self.ws.closed:
            try:
                msg = await self.ws.receive()

                if msg.type == aiohttp.WSMsgType.TEXT:
                    payload = json.loads(msg.data)
                    await self._dispatch(payload)

                elif msg.type == aiohttp.WSMsgType.PING:
                    logger.debug("收到 WebSocket PING")

                elif msg.type == aiohttp.WSMsgType.PONG:
                    logger.debug("收到 WebSocket PONG")

                elif msg.type in {aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR}:
                    logger.warning("WebSocket 连接关闭 (type=%s)", msg.type)
                    break

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("消息监听异常: %s", e)
                break

    async def _dispatch(self, payload: dict):
        """分发收到的消息"""
        cmd = payload.get("cmd", "")
        req_id = (payload.get("headers") or {}).get("req_id", "")

        # 回复 pending 请求
        if req_id and req_id in self.pending_responses:
            future = self.pending_responses.pop(req_id, None)
            if future and not future.done():
                future.set_result(payload)
            return

        # 消息回调
        if cmd in CALLBACK_COMMANDS:
            await self._on_message(payload)
            return

        # ping / 事件回调 — 忽略
        if cmd in {CMD_PING, CMD_EVENT_CALLBACK}:
            return

        logger.debug("未处理的帧: cmd=%s", cmd)

    # ----------------------------------------------------------
    # 消息处理
    # ----------------------------------------------------------

    async def _on_message(self, payload: dict):
        """处理收到的消息回调"""
        body = payload.get("body", {})
        msgtype = body.get("msgtype", "text")
        sender = body.get("from", {})
        sender_id = sender.get("userid", "unknown")
        chat_id = body.get("chatid", sender_id)
        chat_type = body.get("chattype", "single")

        logger.info("📩 收到消息 | from=%s chat=%s type=%s chattype=%s",
                    sender_id, chat_id, msgtype, chat_type)

        # 提取文本内容
        text = ""
        if msgtype == "text":
            text = body.get("text", {}).get("content", "")
        elif msgtype == "mixed":
            for item in body.get("mixed", {}).get("msg_item", []):
                if item.get("msgtype") == "text":
                    text += item.get("text", {}).get("content", "")

        if text:
            logger.info("   内容: %s", text[:200])

        # ========================================================
        # 这里接入你的 AI 回复逻辑
        # 示例: 简单 echo
        # ========================================================

        # 获取回调的 req_id 用于直接回复
        callback_req_id = (payload.get("headers") or {}).get("req_id", "")

        if text.strip().lower() == "ping":
            reply_text = "pong! 🏓"
        elif text.strip().lower() == "help":
            reply_text = (
                "我是 AI Bot，已通过 SDK 长连接在线。\n"
                "试试给我发消息吧！\n"
                "- ping → pong\n"
                "- help → 帮助\n"
            )
        else:
            reply_text = f"收到你的消息: {text}"

        # 发送回复
        await self._send_text(chat_id, reply_text, callback_req_id)

    # ----------------------------------------------------------
    # 发送消息
    # ----------------------------------------------------------

    async def _send_text(self, chat_id: str, content: str, callback_req_id: str = ""):
        """发送文本消息到指定会话"""
        body = {
            "chatid": chat_id,
            "msgtype": "text",
            "text": {"content": content},
        }

        try:
            if callback_req_id:
                # 优先使用被动回复 (关联到用户的消息)
                resp = await self._send_request(
                    CMD_RESPONSE, body, reply_req_id=callback_req_id
                )
            else:
                resp = await self._send_request(CMD_SEND, body)

            errcode = resp.get("body", {}).get("errcode", resp.get("errcode", 0))
            if errcode not in (0, None):
                errmsg = resp.get("body", {}).get("errmsg", resp.get("errmsg", "?"))
                logger.error("发送失败: errcode=%s errmsg=%s", errcode, errmsg)
            else:
                logger.info("✅ 回复已发送 → chat=%s", chat_id)
        except Exception as e:
            logger.error("发送异常: %s", e)

    async def _send_request(
        self, cmd: str, body: dict, reply_req_id: str = "", timeout: float = 15
    ) -> dict:
        """发送请求帧并等待响应"""
        if not self.ws or self.ws.closed:
            raise RuntimeError("WebSocket 未连接")

        if reply_req_id:
            req_id = reply_req_id
        else:
            req_id = new_req_id(cmd)

        future = asyncio.get_running_loop().create_future()
        self.pending_responses[req_id] = future

        try:
            await self.ws.send_json({
                "cmd": cmd,
                "headers": {"req_id": req_id},
                "body": body,
            })
            return await asyncio.wait_for(future, timeout=timeout)
        finally:
            self.pending_responses.pop(req_id, None)


# ============================================================
# 入口
# ============================================================

async def main():
    print("=" * 60)
    print("企业微信 AI Bot SDK 长连接")
    print(f"Bot ID : {BOT_ID}")
    print(f"Secret : {'*' * len(SECRET)}")
    print(f"WS URL : {WS_URL}")
    print("=" * 60)

    client = WeComLongConnection(BOT_ID, SECRET, WS_URL)
    try:
        await client.run()
    except KeyboardInterrupt:
        logger.info("用户中断")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
