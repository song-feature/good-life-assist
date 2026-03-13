"""聊天 SSE 端点"""
import json
import logging
import asyncio

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, AIMessage

from server.core.schemas import ChatRequest
from server.agent.graph import get_graph

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

        try:
            # Run graph in thread pool to not block
            result = await asyncio.to_thread(graph.invoke, input_state)

            # Send ui_commands first
            for cmd in result.get("ui_commands", []):
                yield _format_sse("ui_command", cmd)

            # Send the final message
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
