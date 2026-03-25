"""
VClip job routes — submit and manage processing jobs.
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect

from app.db import create_job, get_job, list_jobs
from app.models import (
    JobCreateRequest,
    JobCreateResponse,
    JobResponse,
    JobStatus,
)
from app.workers.pipeline import (
    register_progress_callback,
    run_pipeline,
    unregister_progress_callback,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])

# Strict regex — fullmatch to prevent suffix injection
SUPPORTED_URL_PATTERN = re.compile(
    r"https?://(www\.)?"
    r"("
    r"youtube\.com/watch\?v=[\w\-]{11}"
    r"|youtu\.be/[\w\-]{11}"
    r"|youtube\.com/live/[\w\-]{11}"
    r"|bilibili\.com/video/(?:BV[\w]{10}|av\d+)"
    r"|b23\.tv/[\w]{7}"
    r")(/?)(\?[\w=&\-]*)?"
)


def _validate_video_url(url: str) -> bool:
    """Validate that the URL is a supported video platform URL (strict)."""
    url = url.strip()
    if not url:
        return False
    # Must be http(s) — block file://, ftp://, etc.
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    # Block SSRF: internal/private IPs
    hostname = parsed.hostname or ""
    if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "[::1]", ""):
        return False
    if hostname.startswith("10.") or hostname.startswith("192.168.") or hostname.startswith("172."):
        return False
    return bool(SUPPORTED_URL_PATTERN.fullmatch(url))


@router.post("", response_model=JobCreateResponse)
async def create_new_job(request: JobCreateRequest, background_tasks: BackgroundTasks):
    """
    Submit a new clipping job.

    Accepts a YouTube URL and processing options.
    Returns immediately with a job_id for status polling.
    """
    if not _validate_video_url(request.url):
        raise HTTPException(
            status_code=400,
            detail="Invalid video URL. Supported: "
                   "youtube.com/watch?v=..., youtu.be/..., youtube.com/live/..., "
                   "bilibili.com/video/BVxxx, b23.tv/xxx"
        )

    job_id = await create_job(request)

    # Estimate processing time (rough: 1 min per 10 min of video)
    estimated_time = 120  # 2 minutes default estimate

    # Start pipeline in background
    background_tasks.add_task(
        run_pipeline, job_id, request.url, request.options
    )

    logger.info(f"Job {job_id} created for {request.url}")

    return JobCreateResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        estimated_time=estimated_time,
    )


@router.get("", response_model=list[dict])
async def list_all_jobs(limit: int = 50, offset: int = 0):
    """List all jobs (summary)."""
    return await list_jobs(limit=limit, offset=offset)


def _is_valid_hex_id(val: str, length: int = 16) -> bool:
    return bool(val) and len(val) == length and all(c in "0123456789abcdef" for c in val)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    """
    Get job status, highlights, and clips.

    Returns full job details including detected highlights
    and generated clip download URLs.
    """
    if not _is_valid_hex_id(job_id):
        raise HTTPException(status_code=400, detail="Invalid job_id format")
    job = await get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job


# ══════════════════════════════════════════════════════════════════
#  WebSocket for real-time progress
# ══════════════════════════════════════════════════════════════════

ws_router = APIRouter()


@ws_router.websocket("/ws/jobs/{job_id}")
async def websocket_job_progress(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time progress updates.

    Clients connect and receive JSON progress messages:
    {
        "job_id": "...",
        "status": "downloading",
        "progress": 15.0,
        "message": "Downloading video...",
        "timestamp": "..."
    }
    """
    # TODO: add authentication (e.g. token query param) to prevent unauthorized access
    # Validate job_id format to prevent abuse
    if not job_id or not all(c in "0123456789abcdef" for c in job_id) or len(job_id) != 16:
        await websocket.close(code=1008, reason="Invalid job_id")
        return
    await websocket.accept()
    logger.info(f"WebSocket connected for job {job_id}")

    async def send_update(data: str):
        try:
            await websocket.send_text(data)
        except Exception:
            pass

    register_progress_callback(job_id, send_update)

    try:
        # Send current status immediately
        job = await get_job(job_id)
        if job:
            from app.models import ProgressUpdate
            initial = ProgressUpdate(
                job_id=job_id,
                status=job.status,
                progress=job.progress,
                message=job.message,
            )
            await websocket.send_text(initial.model_dump_json())

        # Keep connection open until client disconnects or job completes
        while True:
            try:
                # Wait for client messages (keepalive / close)
                data = await asyncio.wait_for(
                    websocket.receive_text(), timeout=60.0
                )
                # Client can send "ping" for keepalive
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send keepalive
                try:
                    await websocket.send_text('{"type":"keepalive"}')
                except Exception:
                    break
            except WebSocketDisconnect:
                break

    finally:
        unregister_progress_callback(job_id, send_update)
        logger.info(f"WebSocket disconnected for job {job_id}")
