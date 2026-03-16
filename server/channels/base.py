"""通道基类 - 所有通道实现继承此类"""
import contextvars
import logging
import queue as queue_mod
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Optional

from langchain_core.messages import HumanMessage, AIMessage

from server.agent.graph import get_graph
from server.agent.progress import progress_queue, channel_context, session_data

logger = logging.getLogger("server.channels.base")


class BaseChannel(ABC):
    """通道基类"""
    channel_id: str = ""
    channel_type: str = ""  # "web" | "im"
    display_name: str = ""
    description: str = ""

    # 配置项 schema，用于前端动态渲染配置表单
    config_schema: list[dict] = []

    @abstractmethod
    def start(self) -> None:
        """启动通道（可能阻塞，在守护线程中运行）"""
        ...

    @abstractmethod
    def stop(self) -> None:
        """停止通道"""
        ...

    @abstractmethod
    def test_connection(self, config: dict) -> tuple[bool, str]:
        """测试连接，返回 (success, message)"""
        ...

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """通道是否正在运行"""
        ...

    def configure(self, config: dict) -> None:
        """接收配置参数"""
        self.config = config


class BaseIMChannel(BaseChannel):
    """IM 通道基类 - 封装 Agent 调用逻辑"""
    channel_type: str = "im"

    def _invoke_agent(
        self,
        user_message: str,
        on_progress: Optional[Callable[[dict], None]] = None,
    ) -> str:
        """调用 Agent 并返回文本回复。

        Args:
            user_message: 用户消息文本
            on_progress: 可选回调，接收 progress/token/usage 事件字典。
                         当提供回调时，graph.invoke 在子线程中运行，
                         当前线程持续消费 progress queue 并调用回调。
        """
        graph = get_graph()
        input_state = {
            "messages": [HumanMessage(content=user_message)],
            "current_module": None,
            "ui_commands": [],
            "intent": None,
        }

        q: queue_mod.Queue = queue_mod.Queue()
        ctx = contextvars.copy_context()
        ctx.run(progress_queue.set, q)
        ctx.run(channel_context.set, "im")
        ctx.run(session_data.set, {})

        try:
            if on_progress is None:
                # 无回调 — 直接同步调用
                result = ctx.run(graph.invoke, input_state)
            else:
                # 有回调 — 在子线程运行 graph，当前线程消费 queue
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(ctx.run, graph.invoke, input_state)

                    while not future.done():
                        try:
                            event = q.get(timeout=0.3)
                            on_progress(event)
                        except queue_mod.Empty:
                            continue

                    # 排空残留事件
                    while not q.empty():
                        try:
                            on_progress(q.get_nowait())
                        except queue_mod.Empty:
                            break

                    result = future.result()

            messages = result.get("messages", [])
            for msg in reversed(messages):
                if isinstance(msg, AIMessage) and msg.content:
                    return msg.content
            return "抱歉，我没有生成回复。"
        except Exception as e:
            logger.error(f"[{self.channel_id}] Agent 调用失败: {e}", exc_info=True)
            return f"处理消息时发生错误: {e}"
