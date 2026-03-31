"""
VClip analytics dashboard — usage stats and health monitoring.

Endpoints:
  GET /api/v1/analytics/stats    — aggregate usage stats
  GET /api/v1/analytics/health   — detailed system health

Phase 5 feature.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Request

from app.config import settings
from app.db import get_usage_stats
from app.middleware.api_key import get_api_key_info
from app.models import UsageStats

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

_START_TIME = time.time()


@router.get("/stats", response_model=UsageStats)
async def get_stats(
    key_record: Optional[dict] = Depends(get_api_key_info),
):
    """
    Aggregate usage statistics.

    Returns totals for jobs, clips, and per-status breakdown.
    API key auth recommended but not required for self-hosted instances.
    """
    raw = await get_usage_stats()

    # Infer platform distribution from URL patterns (best-effort from DB)
    top_platforms: dict[str, int] = {}
    try:
        import aiosqlite
        async with aiosqlite.connect(str(settings.db_path)) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT url, COUNT(*) as cnt FROM jobs GROUP BY "
                "CASE "
                "  WHEN url LIKE '%bilibili%' OR url LIKE '%b23.tv%' THEN 'bilibili' "
                "  WHEN url LIKE '%twitch%' THEN 'twitch' "
                "  ELSE 'youtube' "
                "END "
                "ORDER BY cnt DESC"
            )
            # Rewrite: use simple aggregation
            cursor2 = await db.execute(
                """SELECT
                   SUM(CASE WHEN url LIKE '%bilibili%' OR url LIKE '%b23.tv%' THEN 1 ELSE 0 END) as bilibili,
                   SUM(CASE WHEN url LIKE '%twitch%' THEN 1 ELSE 0 END) as twitch,
                   SUM(CASE WHEN url NOT LIKE '%bilibili%' AND url NOT LIKE '%b23.tv%' AND url NOT LIKE '%twitch%' THEN 1 ELSE 0 END) as youtube
                   FROM jobs"""
            )
            row = await cursor2.fetchone()
            if row:
                top_platforms = {
                    "youtube": row["youtube"] or 0,
                    "bilibili": row["bilibili"] or 0,
                    "twitch": row["twitch"] or 0,
                }
    except Exception as e:
        logger.debug(f"Platform stats query failed: {e}")

    return UsageStats(
        total_jobs=raw.get("total_jobs", 0),
        total_clips=raw.get("total_clips", 0),
        jobs_today=raw.get("jobs_today", 0),
        clips_today=raw.get("clips_today", 0),
        jobs_by_status=raw.get("jobs_by_status", {}),
        top_platforms=top_platforms,
    )


@router.get("/health")
async def detailed_health(request: Request):
    """
    Detailed system health check.

    Returns:
      - API uptime
      - Disk usage for clips directory
      - Whisper model configuration
      - Worker queue status
      - x402 configuration
    """
    uptime_seconds = time.time() - _START_TIME

    # Disk stats
    disk_info: dict = {}
    try:
        clips_dir = settings.clips_dir.resolve()
        if clips_dir.exists():
            import shutil
            total, used, free = shutil.disk_usage(clips_dir)
            disk_info = {
                "clips_dir": str(clips_dir),
                "total_gb": round(total / 1e9, 1),
                "used_gb": round(used / 1e9, 1),
                "free_gb": round(free / 1e9, 1),
                "usage_pct": round(used / total * 100, 1) if total else 0,
            }
    except Exception as e:
        disk_info = {"error": str(e)}

    # Count active jobs
    active_jobs = 0
    try:
        import aiosqlite
        async with aiosqlite.connect(str(settings.db_path)) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM jobs WHERE status NOT IN ('complete', 'failed')"
            )
            row = await cursor.fetchone()
            active_jobs = row[0] if row else 0
    except Exception:
        pass

    return {
        "status": "healthy",
        "uptime_seconds": round(uptime_seconds, 1),
        "version": "1.0.0",
        "config": {
            "whisper_model": settings.whisper_model,
            "whisper_device": settings.whisper_device,
            "max_concurrent_jobs": settings.max_concurrent_jobs,
            "llm_reranking": settings.llm_rerank_enabled,
            "openai_model": settings.openai_model if settings.llm_rerank_enabled else None,
        },
        "queue": {
            "active_jobs": active_jobs,
            "max_concurrent": settings.max_concurrent_jobs,
        },
        "disk": disk_info,
        "x402": {
            "enabled": bool(settings.x402_wallet_address),
            "price_per_clip": settings.x402_price_per_clip,
            "network": settings.x402_network,
            "wallet": settings.x402_wallet_address or "not configured",
        },
        "platforms": {
            "youtube": True,
            "bilibili": True,
            "twitch": True,
        },
    }
