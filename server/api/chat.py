"""聊天 SSE 端点 - 支持实时进度推送和流式 token 输出"""
import json
import logging
import asyncio
import contextvars
import queue

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, AIMessage

from server.core.schemas import ChatRequest
from server.agent.graph import get_graph
from server.agent.progress import progress_queue, channel_context, session_data

logger = logging.getLogger("server.api.chat")
router = APIRouter(tags=["chat"])


def _format_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    async def event_generator():
        graph = get_graph()

        input_state = {
            "messages": [HumanMessage(content=request.message)],
            "current_module": None,
            "ui_commands": [],
            "intent": None,
        }

        # 创建 progress queue 并注入到 contextvars
        q: queue.Queue = queue.Queue()
        ctx = contextvars.copy_context()
        ctx.run(progress_queue.set, q)
        ctx.run(channel_context.set, "web")
        ctx.run(session_data.set, {})

        tokens_streamed = False

        try:
            loop = asyncio.get_event_loop()
            # 在线程中执行 graph.invoke，同时携带 contextvars 上下文
            future = loop.run_in_executor(
                None,
                lambda: ctx.run(graph.invoke, input_state),
            )

            # 边消费事件边等待结果
            while not future.done():
                try:
                    event = await asyncio.to_thread(q.get, timeout=0.1)
                    evt_type = event.get("_type")
                    if evt_type == "token":
                        tokens_streamed = True
                        yield _format_sse("message", {"content": event["content"]})
                    elif evt_type == "usage":
                        yield _format_sse("usage", {"provider": event.get("provider", ""), "model": event.get("model", ""), "usage": event.get("usage", {})})
                    else:
                        yield _format_sse("progress", {"step": event.get("step", ""), "detail": event.get("detail", "")})
                except queue.Empty:
                    continue

            result = future.result()

            # 排空 queue 中可能残留的事件
            while not q.empty():
                try:
                    event = q.get_nowait()
                    evt_type = event.get("_type")
                    if evt_type == "token":
                        tokens_streamed = True
                        yield _format_sse("message", {"content": event["content"]})
                    elif evt_type == "usage":
                        yield _format_sse("usage", {"provider": event.get("provider", ""), "model": event.get("model", ""), "usage": event.get("usage", {})})
                    else:
                        yield _format_sse("progress", {"step": event.get("step", ""), "detail": event.get("detail", "")})
                except queue.Empty:
                    break

            # Send ui_commands first
            for cmd in result.get("ui_commands", []):
                yield _format_sse("ui_command", cmd)

            # Send the final message only if not already streamed
            if not tokens_streamed:
                messages = result.get("messages", [])
                for msg in messages:
                    if isinstance(msg, AIMessage) and msg.content:
                        yield _format_sse("message", {"content": msg.content})

            yield _format_sse("done", {})

        except Exception as e:
            logger.error(f"聊天处理失败: {e}", exc_info=True)
            yield _format_sse("error", {"message": str(e)})
            yield _format_sse("done", {})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
