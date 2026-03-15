"""Agent 进度事件系统 - 通过 contextvars 在同步节点中发送进度到异步 SSE"""
import contextvars
import queue

progress_queue: contextvars.ContextVar[queue.Queue | None] = contextvars.ContextVar(
    "progress_queue", default=None
)

# 通道上下文: "web"(默认) 或 "im"
channel_context: contextvars.ContextVar[str] = contextvars.ContextVar(
    "channel_context", default="web"
)

# 会话级数据共享：同一次 graph.invoke 中 tools 之间共享已获取的数据
session_data: contextvars.ContextVar[dict | None] = contextvars.ContextVar(
    "session_data", default=None
)


def get_channel() -> str:
    """获取当前通道类型"""
    return channel_context.get("web")


def get_session_store() -> dict:
    """获取当前会话的共享数据字典，不存在则返回空 dict（不会写入 ContextVar）"""
    store = session_data.get()
    if store is None:
        return {}
    return store


def emit_progress(step: str, detail: str = ""):
    """发送一个进度事件到当前上下文的 queue（如果存在）"""
    q = progress_queue.get(None)
    if q is not None:
        q.put_nowait({"_type": "progress", "step": step, "detail": detail})


def emit_token(content: str):
    """发送一个流式 token 到当前上下文的 queue"""
    q = progress_queue.get(None)
    if q is not None:
        q.put_nowait({"_type": "token", "content": content})


def emit_usage(provider: str, model: str, usage: dict | None = None):
    """发送模型和 token 用量信息"""
    q = progress_queue.get(None)
    if q is not None:
        q.put_nowait({
            "_type": "usage",
            "provider": provider,
            "model": model,
            "usage": usage or {},
        })
