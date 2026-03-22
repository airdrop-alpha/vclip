"""
VClip API — FastAPI application entry point.

VTuber Automatic Clip/Highlight Editor backend.

Run with:
    python -m app.main
    uvicorn app.main:app --reload
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_db
from app.routes.clips import export_router, router as clips_router
from app.routes.jobs import router as jobs_router, ws_router

# ── Logging ──────────────────────────────────────────────────

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("vclip")

# Quiet noisy libraries
for lib in ["httpcore", "httpx", "urllib3", "websockets"]:
    logging.getLogger(lib).setLevel(logging.WARNING)


# ── Lifespan ─────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    logger.info("VClip backend starting up")
    settings.ensure_dirs()
    await init_db()
    logger.info(f"Data dir: {settings.data_dir.resolve()}")
    logger.info(f"Whisper model: {settings.whisper_model} ({settings.whisper_device})")
    yield
    logger.info("VClip backend shutting down")


# ── App ──────────────────────────────────────────────────────

app = FastAPI(
    title="VClip API",
    description="VTuber Automatic Clip/Highlight Editor — AI-powered clipping backend",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https://.*\.vclip\.pages\.dev|https://.*\.trycloudflare\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(jobs_router)
app.include_router(clips_router)
app.include_router(export_router)
app.include_router(ws_router)


# ── Root endpoint ────────────────────────────────────────────

@app.get("/", tags=["health"])
async def root():
    """Health check / API info."""
    return {
        "service": "VClip API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "whisper_model": settings.whisper_model,
        "data_dir": str(settings.data_dir.resolve()),
    }


# ── Run ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info",
    )
