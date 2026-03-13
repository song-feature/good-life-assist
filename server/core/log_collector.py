"""内存日志收集器 - 捕获应用日志供前端查看"""
import logging
from collections import deque
from datetime import datetime
from threading import Lock


class LogRecord:
    __slots__ = ("timestamp", "level", "logger_name", "message")

    def __init__(self, timestamp: str, level: str, logger_name: str, message: str):
        self.timestamp = timestamp
        self.level = level
        self.logger_name = logger_name
        self.message = message

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "level": self.level,
            "logger": self.logger_name,
            "message": self.message,
        }


class MemoryLogHandler(logging.Handler):
    """将日志写入内存环形缓冲区"""

    def __init__(self, capacity: int = 500):
        super().__init__()
        self._buffer: deque[LogRecord] = deque(maxlen=capacity)
        self._lock = Lock()

    def emit(self, record: logging.LogRecord):
        try:
            entry = LogRecord(
                timestamp=datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                level=record.levelname,
                logger_name=record.name,
                message=self.format(record),
            )
            with self._lock:
                self._buffer.append(entry)
        except Exception:
            self.handleError(record)

    def get_logs(
        self,
        level: str | None = None,
        logger_name: str | None = None,
        keyword: str | None = None,
        limit: int = 200,
    ) -> list[dict]:
        with self._lock:
            logs = list(self._buffer)

        if level:
            level_upper = level.upper()
            logs = [r for r in logs if r.level == level_upper]

        if logger_name:
            logs = [r for r in logs if logger_name in r.logger_name]

        if keyword:
            kw = keyword.lower()
            logs = [r for r in logs if kw in r.message.lower()]

        # 最新的在前
        logs = logs[-limit:]
        logs.reverse()
        return [r.to_dict() for r in logs]

    def clear(self):
        with self._lock:
            self._buffer.clear()


# 全局实例
_handler: MemoryLogHandler | None = None


def get_log_handler() -> MemoryLogHandler:
    global _handler
    if _handler is None:
        _handler = MemoryLogHandler(capacity=500)
        _handler.setFormatter(logging.Formatter("%(message)s"))
    return _handler


def install_log_handler(min_level: int = logging.WARNING):
    """挂载到 root logger，捕获 WARNING 及以上级别的日志"""
    handler = get_log_handler()
    handler.setLevel(min_level)
    root = logging.getLogger()
    if handler not in root.handlers:
        root.addHandler(handler)
