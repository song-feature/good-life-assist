"""飞书 IM 通道 - WebSocket 长连接，支持实时进度反馈和流式卡片更新"""
import json
import logging
import threading
import time

from server.channels.base import BaseIMChannel

logger = logging.getLogger("server.channels.feishu")

# PATCH 卡片更新的最小间隔（秒），避免频率过高被限流
_PATCH_INTERVAL = 0.8


class FeishuChannel(BaseIMChannel):
    channel_id = "feishu"
    channel_type = "im"
    display_name = "飞书"
    description = "通过飞书机器人接收和回复消息，使用 WebSocket 长连接"

    config_schema = [
        {"key": "app_id", "label": "App ID", "type": "text", "required": True,
         "description": "飞书应用的 App ID"},
        {"key": "app_secret", "label": "App Secret", "type": "password", "required": True,
         "description": "飞书应用的 App Secret"},
    ]

    def __init__(self):
        self.config: dict = {}
        self._running = False
        self._ws_client = None
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        return self._running

    def configure(self, config: dict) -> None:
        self.config = config

    def start(self) -> None:
        """启动 WebSocket 长连接（阻塞）"""
        import asyncio

        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)

        try:
            import lark_oapi as lark
            from lark_oapi.ws import Client as WsClient
        except ImportError:
            raise RuntimeError("请安装 lark-oapi: pip install lark-oapi")

        import lark_oapi.ws.client as _ws_mod
        _ws_mod.loop = new_loop

        app_id = self.config.get("app_id", "")
        app_secret = self.config.get("app_secret", "")
        if not app_id or not app_secret:
            raise ValueError("飞书通道需要配置 app_id 和 app_secret")

        event_handler = (
            lark.EventDispatcherHandler.builder("", "")
            .register_p2_im_message_receive_v1(self._on_message)
            .build()
        )

        self._ws_client = WsClient(
            app_id=app_id,
            app_secret=app_secret,
            event_handler=event_handler,
            log_level=lark.LogLevel.INFO,
        )

        self._running = True
        logger.info("飞书通道 WebSocket 连接启动中...")

        try:
            self._ws_client.start()
        except Exception as e:
            self._running = False
            raise

    def stop(self) -> None:
        """停止通道"""
        self._running = False
        self._stop_event.set()
        self._ws_client = None
        logger.info("飞书通道已停止")

    # ------------------------------------------------------------------
    # 消息处理
    # ------------------------------------------------------------------

    def _on_message(self, event) -> None:
        """SDK 回调入口 — 必须立即返回，不阻塞 event loop"""
        t = threading.Thread(target=self._process_message, args=(event,), daemon=True)
        t.start()

    def _process_message(self, event) -> None:
        """在独立线程中处理消息，支持实时进度和流式输出"""
        try:
            msg = event.event.message
            msg_type = msg.message_type

            if msg_type != "text":
                self._reply(msg.message_id, "抱歉，目前只支持文字消息。")
                return

            content = json.loads(msg.content)
            text = content.get("text", "").strip()
            if not text:
                return

            if msg.mentions:
                for mention in msg.mentions:
                    text = text.replace(f"@_{mention.key}", "").strip()

            if not text:
                return

            logger.info(f"飞书收到消息: {text[:50]}...")

            # 1) 立即回复"处理中"卡片，拿到 reply_message_id
            reply_msg_id = self._reply_initial(msg.message_id)
            if not reply_msg_id:
                # 回复失败，降级为无进度模式
                reply_text = self._invoke_agent(text)
                self._reply(msg.message_id, reply_text)
                return

            # 2) 用进度回调驱动卡片实时更新
            state = _StreamingState()

            def on_progress(evt: dict):
                evt_type = evt.get("_type")
                if evt_type == "progress":
                    step = evt.get("step", "")
                    detail = evt.get("detail", "")
                    state.set_progress(step, detail)
                elif evt_type == "token":
                    state.append_token(evt.get("content", ""))
                # usage 事件不需要展示

                # 节流：距上次 PATCH 至少 _PATCH_INTERVAL 秒
                now = time.time()
                if now - state.last_patch_time >= _PATCH_INTERVAL:
                    card_text = state.render()
                    self._patch_card(reply_msg_id, card_text)
                    state.last_patch_time = now

            reply_text = self._invoke_agent(text, on_progress=on_progress)

            # 3) 最终更新卡片为完整回复
            self._patch_card(reply_msg_id, reply_text)

        except Exception as e:
            logger.error(f"飞书消息处理失败: {e}", exc_info=True)
            try:
                self._reply(event.event.message.message_id, f"处理消息时出错: {e}")
            except Exception:
                pass

    # ------------------------------------------------------------------
    # 飞书 API 封装
    # ------------------------------------------------------------------

    def _get_client(self):
        """获取 lark API client"""
        import lark_oapi as lark
        return lark.Client.builder() \
            .app_id(self.config.get("app_id", "")) \
            .app_secret(self.config.get("app_secret", "")) \
            .build()

    def _reply_initial(self, user_message_id: str) -> str | None:
        """回复一条"处理中"卡片，返回新消息的 message_id（用于后续 PATCH）"""
        try:
            from lark_oapi.api.im.v1 import (
                ReplyMessageRequest, ReplyMessageRequestBody,
            )
            client = self._get_client()
            body = ReplyMessageRequestBody.builder() \
                .msg_type("interactive") \
                .content(json.dumps(
                    self._progress_card("正在思考...", ""),
                    ensure_ascii=False,
                )) \
                .build()

            request = ReplyMessageRequest.builder() \
                .message_id(user_message_id) \
                .request_body(body) \
                .build()

            response = client.im.v1.message.reply(request)
            if response.success() and response.data:
                return response.data.message_id
            logger.error(f"飞书初始回复失败: {response.code} - {response.msg}")
            return None
        except Exception as e:
            logger.error(f"飞书初始回复异常: {e}", exc_info=True)
            return None

    def _patch_card(self, message_id: str, text: str) -> None:
        """通过 PATCH 更新已发送的卡片内容"""
        try:
            from lark_oapi.api.im.v1 import (
                PatchMessageRequest, PatchMessageRequestBody,
            )
            client = self._get_client()
            body = PatchMessageRequestBody.builder() \
                .content(json.dumps(
                    self._text_to_card(text),
                    ensure_ascii=False,
                )) \
                .build()

            request = PatchMessageRequest.builder() \
                .message_id(message_id) \
                .request_body(body) \
                .build()

            response = client.im.v1.message.patch(request)
            if not response.success():
                logger.warning(f"飞书 PATCH 卡片失败: {response.code} - {response.msg}")
        except Exception as e:
            logger.warning(f"飞书 PATCH 卡片异常: {e}")

    def _reply(self, message_id: str, text: str) -> None:
        """回复飞书消息（降级用：不需要后续更新时使用）"""
        try:
            from lark_oapi.api.im.v1 import (
                ReplyMessageRequest, ReplyMessageRequestBody,
            )
            client = self._get_client()
            body = ReplyMessageRequestBody.builder() \
                .msg_type("interactive") \
                .content(json.dumps(self._text_to_card(text), ensure_ascii=False)) \
                .build()

            request = ReplyMessageRequest.builder() \
                .message_id(message_id) \
                .request_body(body) \
                .build()

            response = client.im.v1.message.reply(request)
            if not response.success():
                logger.error(f"飞书回复失败: {response.code} - {response.msg}")
        except Exception as e:
            logger.error(f"飞书回复异常: {e}", exc_info=True)

    # ------------------------------------------------------------------
    # 卡片格式构建
    # ------------------------------------------------------------------

    @staticmethod
    def _text_to_card(text: str) -> dict:
        """将文本转为飞书卡片消息格式"""
        return {
            "config": {"wide_screen_mode": True},
            "elements": [
                {"tag": "markdown", "content": text},
            ],
        }

    @staticmethod
    def _progress_card(step: str, detail: str) -> dict:
        """构建进度提示卡片"""
        parts = [f"**{step}**"]
        if detail:
            parts.append(detail)
        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": "处理中..."},
                "template": "blue",
            },
            "elements": [
                {"tag": "markdown", "content": "\n".join(parts)},
            ],
        }

    # ------------------------------------------------------------------
    # 连接测试
    # ------------------------------------------------------------------

    def test_connection(self, config: dict) -> tuple[bool, str]:
        """测试飞书应用凭证是否有效"""
        app_id = config.get("app_id", "")
        app_secret = config.get("app_secret", "")
        if not app_id or not app_secret:
            return False, "请提供 App ID 和 App Secret"

        try:
            import urllib.request
            import json as json_mod

            data = json_mod.dumps({
                "app_id": app_id,
                "app_secret": app_secret,
            }).encode()

            req = urllib.request.Request(
                "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json_mod.loads(resp.read())
                if result.get("code") == 0:
                    return True, "连接成功，凭证有效"
                else:
                    return False, f"凭证无效: {result.get('msg', '未知错误')}"
        except Exception as e:
            return False, f"连接测试失败: {e}"


# ----------------------------------------------------------------------
# 流式状态管理（线程内使用，无需加锁）
# ----------------------------------------------------------------------

class _StreamingState:
    """跟踪 Agent 执行过程中的进度和流式 token"""

    def __init__(self):
        self.current_step: str = ""
        self.current_detail: str = ""
        self.token_buffer: list[str] = []
        self.last_patch_time: float = 0.0

    def set_progress(self, step: str, detail: str):
        self.current_step = step
        self.current_detail = detail

    def append_token(self, token: str):
        self.token_buffer.append(token)

    def render(self) -> str:
        """渲染当前状态为卡片文本"""
        parts: list[str] = []

        # 进度信息
        if self.current_step:
            progress_line = f"**{self.current_step}**"
            if self.current_detail:
                progress_line += f"  {self.current_detail}"
            parts.append(progress_line)

        # 已累积的流式 token
        if self.token_buffer:
            accumulated = "".join(self.token_buffer)
            if parts:
                parts.append("---")
            parts.append(accumulated)

        return "\n".join(parts) if parts else "正在处理..."
