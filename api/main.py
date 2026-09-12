"""FastAPI application entrypoint for Smart Watchdog backend."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import load_config
from api.routes import (
    health,
    institutions,
    rankings,
    accounts,
    opinion,
    whatif,
)

logger = logging.getLogger("api.main")
cfg = load_config()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Cold start lifecycle: initialize S3 parquet cache if present."""
    logger.info("Starting up FastAPI application...")
    # Infra hook: S3 cold-start parquet cache loading will happen here
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


@app.get("/")
async def root():
    return {
        "service": "Smart Watchdog API",
        "docs": "/docs",
        "status": "online",
    }
