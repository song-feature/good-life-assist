"""Agent 进度事件系统 - 通过 contextvars 在同步节点中发送进度到异步 SSE"""
import contextvars
import queue

progress_queue: contextvars.ContextVar[queue.Queue | None] = contextvars.ContextVar(
    "progress_queue", default=None
)


def emit_progress(step: str, detail: str = ""):
    """发送一个进度事件到当前上下文的 queue（如果存在）"""
    q = progress_queue.get(None)
    if q is not None:
        q.put_nowait({"step": step, "detail": detail})
