"""
VClip processing pipeline — orchestrates the full workflow.

download → transcribe → parse chat → detect highlights → generate subtitles → extract clips

Runs synchronously in a background thread (no Celery dependency for MVP).
Can be upgraded to Celery tasks later.
"""
from __future__ import annotations

import asyncio
import json
import logging
import traceback
from pathlib import Path
from typing import Any, Callable, Optional

from app.config import settings
from app.models import (
    AspectRatio,
    ClipInfo,
    Highlight,
    JobCreateRequest,
    JobMetadata,
    JobOptions,
    JobStatus,
    ProgressUpdate,
    SubtitleStyle,
)

logger = logging.getLogger(__name__)

# Semaphore to limit concurrent pipeline executions
_pipeline_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    """Lazy-init the pipeline semaphore (must be called inside a running loop)."""
    global _pipeline_semaphore
    if _pipeline_semaphore is None:
        _pipeline_semaphore = asyncio.Semaphore(settings.max_concurrent_jobs)
    return _pipeline_semaphore


# Global progress callbacks registry (job_id -> callback)
_progress_callbacks: dict[str, list[Callable]] = {}


def register_progress_callback(job_id: str, callback: Callable) -> None:
    """Register a WebSocket callback for progress updates."""
    if job_id not in _progress_callbacks:
        _progress_callbacks[job_id] = []
    _progress_callbacks[job_id].append(callback)


def unregister_progress_callback(job_id: str, callback: Callable) -> None:
    """Remove a progress callback."""
    if job_id in _progress_callbacks:
        _progress_callbacks[job_id] = [
            cb for cb in _progress_callbacks[job_id] if cb is not callback
        ]
        if not _progress_callbacks[job_id]:
            del _progress_callbacks[job_id]


async def _notify_progress(job_id: str, status: JobStatus, progress: float, message: str) -> None:
    """Send progress update to registered WebSocket callbacks and update DB."""
    from app.db import update_job_status

    await update_job_status(job_id, status, progress, message)

    update = ProgressUpdate(
        job_id=job_id,
        status=status,
        progress=progress,
        message=message,
    )

    callbacks = _progress_callbacks.get(job_id, [])
    for cb in callbacks:
        try:
            await cb(update.model_dump_json())
        except Exception as e:
            logger.debug(f"Progress callback error: {e}")


async def run_pipeline(job_id: str, url: str, options: JobOptions) -> None:
    """
    Run the full VClip processing pipeline.

    Stages:
      1. Download video + extract audio (0–20%)
      2. Transcribe audio (20–45%)
      3. Parse live chat (45–55%)
      4. Detect highlights (55–70%)
      5. Generate subtitles (70–80%)
      6. Extract clips (80–100%)
    """
    from app.db import save_clip, save_highlights, update_job_metadata, update_job_status
    from app.services.chat_parser import parse_live_chat
    from app.services.clipper import extract_clips_batch
    from app.services.downloader import download_video
    from app.services.highlight import detect_highlights
    from app.services.subtitles import generate_subtitles_for_highlights
    from app.services.transcriber import transcribe_multilingual

    sem = _get_semaphore()
    if sem.locked():
        await _notify_progress(job_id, JobStatus.QUEUED, 0.0, "Waiting for available slot...")

    async with sem:
        try:
            # ── Stage 1: Download ────────────────────────────────
            await _notify_progress(
                job_id, JobStatus.DOWNLOADING, 5.0, "Downloading video..."
            )

            # Run blocking download in thread pool
            loop = asyncio.get_event_loop()
            download_result = await loop.run_in_executor(
                None, download_video, url, job_id
            )

            await _notify_progress(
                job_id, JobStatus.DOWNLOADING, 20.0,
                f"Downloaded: {download_result.title} ({download_result.duration:.0f}s)"
            )

            # Save metadata
            metadata = JobMetadata(
                title=download_result.title,
                channel=download_result.channel,
                duration=download_result.duration,
                upload_date=download_result.upload_date,
                thumbnail_url=download_result.thumbnail_url,
            )
            await update_job_metadata(job_id, metadata)

            # ── Stage 2: Transcribe ──────────────────────────────
            await _notify_progress(
                job_id, JobStatus.TRANSCRIBING, 25.0, "Transcribing audio..."
            )

            transcript = await loop.run_in_executor(
                None,
                transcribe_multilingual,
                download_result.audio_path,
                options.languages,
            )

            await _notify_progress(
                job_id, JobStatus.TRANSCRIBING, 45.0,
                f"Transcribed: {len(transcript)} segments"
            )

            # ── Stage 3: Parse chat ──────────────────────────────
            await _notify_progress(
                job_id, JobStatus.PARSING_CHAT, 48.0, "Parsing live chat replay..."
            )

            chat_messages = await loop.run_in_executor(
                None, parse_live_chat, url, job_id
            )

            await _notify_progress(
                job_id, JobStatus.PARSING_CHAT, 55.0,
                f"Chat: {len(chat_messages)} messages" if chat_messages
                else "No live chat found (not a livestream)"
            )

            # ── Stage 4: Detect highlights ───────────────────────
            await _notify_progress(
                job_id, JobStatus.DETECTING, 58.0, "Detecting highlights..."
            )

            highlights = await loop.run_in_executor(
                None,
                detect_highlights,
                transcript,
                chat_messages,
                download_result.audio_path,
                download_result.duration,
                None, None,  # window_size, step_size
                options.min_score,
                None, None, None, None,  # max_gap, weights
            )

            # Limit to max_clips
            highlights = highlights[:options.max_clips]

            await save_highlights(job_id, highlights)

            await _notify_progress(
                job_id, JobStatus.DETECTING, 70.0,
                f"Found {len(highlights)} highlights"
            )

            if not highlights:
                await _notify_progress(
                    job_id, JobStatus.COMPLETE, 100.0,
                    "Complete — no highlights found above threshold"
                )
                return

            # ── Stage 5: Generate subtitles ──────────────────────
            subtitle_paths: dict[str, Path] = {}
            if options.burn_subtitles:
                await _notify_progress(
                    job_id, JobStatus.SUBTITLING, 72.0, "Generating subtitles..."
                )

                subtitle_paths = await loop.run_in_executor(
                    None,
                    generate_subtitles_for_highlights,
                    transcript,
                    highlights,
                    job_id,
                    options.subtitle_style,
                )

                await _notify_progress(
                    job_id, JobStatus.SUBTITLING, 80.0,
                    f"Generated {len(subtitle_paths)} subtitle files"
                )

            # ── Stage 6: Extract clips ───────────────────────────
            await _notify_progress(
                job_id, JobStatus.CLIPPING, 82.0,
                f"Extracting {len(highlights)} clips..."
            )

            clips = await loop.run_in_executor(
                None,
                extract_clips_batch,
                download_result.video_path,
                highlights,
                job_id,
                options.aspect_ratios,
                subtitle_paths,
            )

            # Save clips to DB
            for clip in clips:
                await save_clip(job_id, clip)

            # ── Done ─────────────────────────────────────────────
            await _notify_progress(
                job_id, JobStatus.COMPLETE, 100.0,
                f"Complete! {len(highlights)} highlights, {len(clips)} clips generated"
            )

            logger.info(
                f"[{job_id}] Pipeline complete: "
                f"{len(highlights)} highlights, {len(clips)} clips"
            )

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"[{job_id}] Pipeline failed: {error_msg}")
            logger.debug(traceback.format_exc())

            await _notify_progress(
                job_id, JobStatus.FAILED, 0.0, f"Pipeline failed: {error_msg}"
            )

            from app.db import update_job_status
            await update_job_status(
                job_id, JobStatus.FAILED, error=error_msg
            )


async def run_pipeline_with_retry(
    job_id: str,
    url: str,
    options: "JobOptions",
    max_retries: int = 2,
) -> None:
    """
    Wrap run_pipeline with exponential-backoff retry for transient errors.

    Retries on network / download errors but not on permanent failures
    (e.g. private video, bad URL).
    """
    PERMANENT_ERRORS = (
        "Video unavailable",
        "Private video",
        "Invalid job_id",
        "Authentication required",
        "HTTP Error 403",
        "HTTP Error 404",
    )

    for attempt in range(1, max_retries + 2):
        try:
            await run_pipeline(job_id, url, options)
            return
        except Exception as e:
            err_str = str(e)
            is_permanent = any(p in err_str for p in PERMANENT_ERRORS)

            if is_permanent or attempt > max_retries:
                raise

            wait = 2 ** attempt  # 2s, 4s, …
            logger.warning(
                f"[{job_id}] Attempt {attempt}/{max_retries} failed "
                f"({type(e).__name__}); retrying in {wait}s"
            )
            await asyncio.sleep(wait)
