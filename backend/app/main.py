"""
VClip API — FastAPI application entry point.

VTuber Automatic Clip/Highlight Editor backend.

Run with:
    python -m app.main
    uvicorn app.main:app --reload
"""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_db
from app.routes.clips import export_router, router as clips_router, upload_router
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
    logger.info(f"LLM re-ranking: {'enabled' if settings.llm_rerank_enabled else 'mock'}")
    logger.info(f"x402 price: ${settings.x402_price_per_clip:.2f}/clip")
    yield
    logger.info("VClip backend shutting down")


# ── App ──────────────────────────────────────────────────────

app = FastAPI(
    title="VClip API",
    description=(
        "VTuber Automatic Clip/Highlight Editor — AI-powered clipping backend.\n\n"
        "Supports YouTube, Bilibili, and Twitch.\n\n"
        "**Phase 5**: Public API keys and x402 micropayments available via `/api/v1/keys`."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https://.*\.vclip\.pages\.dev",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request timing middleware ─────────────────────────────────

@app.middleware("http")
async def add_timing_header(request: Request, call_next: Callable) -> Response:
    """Add X-Response-Time header to all responses."""
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Response-Time"] = f"{elapsed_ms:.1f}ms"
    return response


# ── Core routes ───────────────────────────────────────────────

app.include_router(jobs_router)
app.include_router(clips_router)
app.include_router(export_router)
app.include_router(upload_router)
app.include_router(ws_router)

# Phase 4: Auth
try:
    from app.routes.auth import router as auth_router
    app.include_router(auth_router)
    logger.info("Auth routes registered")
except Exception as e:
    logger.warning(f"Auth routes not registered: {e}")

# Phase 5: Public API + analytics
try:
    from app.routes.public_api import router as public_router
    app.include_router(public_router)
    logger.info("Public API routes registered")
except Exception as e:
    logger.warning(f"Public API routes not registered: {e}")

try:
    from app.routes.analytics import router as analytics_router
    app.include_router(analytics_router)
    logger.info("Analytics routes registered")
except Exception as e:
    logger.warning(f"Analytics routes not registered: {e}")


# ── Root endpoints ────────────────────────────────────────────

@app.get("/", tags=["health"])
async def root():
    """Health check / API info."""
    return {
        "service": "VClip API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "platforms": ["youtube", "bilibili", "twitch"],
        "features": {
            "llm_reranking": settings.llm_rerank_enabled,
            "freemium": True,
            "x402_payments": bool(settings.x402_wallet_address),
        },
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Detailed health check."""
    import psutil  # optional

    cpu = None
    mem = None
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory().percent
    except Exception:
        pass

    return {
        "status": "healthy",
        "whisper_model": settings.whisper_model,
        "data_dir": str(settings.data_dir.resolve()),
        "llm_reranking": settings.llm_rerank_enabled,
        "cpu_percent": cpu,
        "mem_percent": mem,
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
