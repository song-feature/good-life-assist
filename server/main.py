"""FastAPI 应用入口"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.config import get_settings
from server.modules.registry import get_registry
from server.core.log_collector import install_log_handler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("server")

# 挂载内存日志收集器，捕获 WARNING+ 级别供前端查看
install_log_handler(min_level=logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    registry = get_registry()
    registry.discover_modules()
    logger.info(f"已注册 {len(registry.modules)} 个模块: {list(registry.modules.keys())}")
    yield
    logger.info("服务关闭")


app = FastAPI(title="Good Life Assistant", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from server.api.chat import router as chat_router
from server.api.admin import router as admin_router
from server.api.modules.stock import router as stock_router

app.include_router(chat_router, prefix="/api")
app.include_router(admin_router, prefix="/api/admin")
app.include_router(stock_router, prefix="/api/modules/stock")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run("server.main:app", host="0.0.0.0", port=settings.server_port, reload=True)
