"""FastAPI application entrypoint for Smart Watchdog backend."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import load_config
from api.services import institution_store, score_cache
from api.routes import (
    health,
    institutions,
    rankings,
    accounts,
    opinion,
    whatif,
    report,
)

logger = logging.getLogger("api.main")
cfg = load_config()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """冷啟動：若私有 S3 上有模型評分檔就改用它。

    Lambda 的部署包不含 ml/，沒有這一步就只剩手寫示範機構。
    下載或載入失敗都不中斷啟動，僅維持既有資料並留下日誌。
    """
    logger.info("Starting up FastAPI application...")
    try:
        cache_dir = score_cache.hydrate()
        if cache_dir and institution_store.reload_from(cache_dir):
            logger.info(
                "Serving %d institutions from S3 scores.",
                len(institution_store.get_all_institutions()),
            )
        else:
            logger.info(
                "S3 scores unavailable; serving %d institutions from local data.",
                len(institution_store.get_all_institutions()),
            )
    except Exception as e:  # pragma: no cover - 啟動不因評分檔問題失敗
        logger.error("Score hydration failed, continuing with local data: %s", e)
    yield
    logger.info("Shutting down FastAPI application...")


app = FastAPI(
    title="小小守護員 Smart Watchdog API",
    description="Inspection risk scoring & explainability API for childcare institutions",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
origins = cfg.get("api", {}).get("cors_origins", ["*"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router)
app.include_router(institutions.router)
app.include_router(rankings.router)
app.include_router(accounts.router)
app.include_router(opinion.router)
app.include_router(whatif.router)
app.include_router(report.router)


@app.get("/")
async def root():
    return {
        "service": "Smart Watchdog API",
        "docs": "/docs",
        "status": "online",
    }
