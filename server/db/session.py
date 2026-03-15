"""数据库会话管理"""
import logging
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from server.config import get_settings

logger = logging.getLogger("server.db")


class Base(DeclarativeBase):
    pass


_engine = None
_SessionLocal = None


def _get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        db_path = Path(settings.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
            echo=False,
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=_get_engine(), expire_on_commit=False)
    return _SessionLocal


def get_session() -> Session:
    return get_session_factory()()


def init_db():
    """建表（如果不存在）"""
    from server.db.models import LLMModel, ModelAssignment, ModuleConfig, ChannelConfig  # noqa: F401
    from server.modules.stock_store.models import WatchlistItem, StockDailyPrice, StockLatestQuote  # noqa: F401

    engine = _get_engine()
    Base.metadata.create_all(engine)
    logger.info("数据库初始化完成")
