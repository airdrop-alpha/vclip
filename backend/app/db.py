"""
VClip SQLite database layer — async via aiosqlite.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import aiosqlite

from app.config import settings
from app.models import (
    AspectRatio,
    ClipInfo,
    Highlight,
    HighlightType,
    JobCreateRequest,
    JobMetadata,
    JobOptions,
    JobResponse,
    JobStatus,
)

logger = logging.getLogger(__name__)

DB_PATH: Path = settings.db_path

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    progress REAL NOT NULL DEFAULT 0.0,
    message TEXT NOT NULL DEFAULT '',
    options_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS highlights (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES jobs(id),
    start_time REAL NOT NULL,
    end_time REAL NOT NULL,
    score REAL NOT NULL,
    highlight_type TEXT NOT NULL DEFAULT 'mixed',
    description TEXT NOT NULL DEFAULT '',
    transcript_snippet TEXT NOT NULL DEFAULT '',
    chat_intensity REAL NOT NULL DEFAULT 0.0,
    audio_energy REAL NOT NULL DEFAULT 0.0,
    keyword_score REAL NOT NULL DEFAULT 0.0,
    contributing_signals TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS clips (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES jobs(id),
    highlight_id TEXT NOT NULL REFERENCES highlights(id),
    aspect_ratio TEXT NOT NULL DEFAULT '16:9',
    file_path TEXT NOT NULL DEFAULT '',
    download_url TEXT NOT NULL DEFAULT '',
    thumbnail_url TEXT NOT NULL DEFAULT '',
    duration REAL NOT NULL DEFAULT 0.0,
    has_subtitles INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_highlights_job ON highlights(job_id);
CREATE INDEX IF NOT EXISTS idx_clips_job ON clips(job_id);
CREATE INDEX IF NOT EXISTS idx_clips_highlight ON clips(highlight_id);
"""


async def init_db() -> None:
    """Initialize database and create tables."""
    settings.ensure_dirs()
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.executescript(SCHEMA)
        await db.commit()
    logger.info(f"Database initialized at {DB_PATH}")


async def _get_db() -> aiosqlite.Connection:
    """Get a database connection."""
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    return db


# ── Job CRUD ───────────────────────────────────────────────────

async def create_job(request: JobCreateRequest) -> str:
    """Create a new job, return job_id."""
    job_id = uuid.uuid4().hex[:16]
    now = datetime.now(timezone.utc).isoformat()
    db = await _get_db()
    try:
        await db.execute(
            """INSERT INTO jobs (id, url, status, progress, message, options_json, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                job_id,
                request.url,
                JobStatus.PENDING.value,
                0.0,
                "Job created",
                request.options.model_dump_json(),
                now,
                now,
            ),
        )
        await db.commit()
    finally:
        await db.close()
    logger.info(f"Created job {job_id} for URL: {request.url}")
    return job_id


async def get_job(job_id: str) -> Optional[JobResponse]:
    """Get job by ID with all highlights and clips."""
    db = await _get_db()
    try:
        cursor = await db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = await cursor.fetchone()
        if not row:
            return None

        # Parse stored JSON
        options = JobOptions.model_validate_json(row["options_json"]) if row["options_json"] != "{}" else None
        metadata_raw = row["metadata_json"]
        metadata = JobMetadata.model_validate_json(metadata_raw) if metadata_raw and metadata_raw != "{}" else None

        # Fetch highlights
        cursor = await db.execute(
            "SELECT * FROM highlights WHERE job_id = ? ORDER BY score DESC", (job_id,)
        )
        highlight_rows = await cursor.fetchall()
        highlights = []
        for h in highlight_rows:
            highlights.append(
                Highlight(
                    id=h["id"],
                    start_time=h["start_time"],
                    end_time=h["end_time"],
                    score=h["score"],
                    highlight_type=HighlightType(h["highlight_type"]),
                    description=h["description"],
                    transcript_snippet=h["transcript_snippet"],
                    chat_intensity=h["chat_intensity"],
                    audio_energy=h["audio_energy"],
                    keyword_score=h["keyword_score"],
                    contributing_signals=json.loads(h["contributing_signals"]),
                )
            )

        # Fetch clips
        cursor = await db.execute(
            "SELECT * FROM clips WHERE job_id = ? ORDER BY duration DESC", (job_id,)
        )
        clip_rows = await cursor.fetchall()
        clips = []
        for c in clip_rows:
            clips.append(
                ClipInfo(
                    id=c["id"],
                    highlight_id=c["highlight_id"],
                    aspect_ratio=AspectRatio(c["aspect_ratio"]),
                    file_path=c["file_path"],
                    download_url=c["download_url"],
                    thumbnail_url=c["thumbnail_url"],
                    duration=c["duration"],
                    has_subtitles=bool(c["has_subtitles"]),
                )
            )

        return JobResponse(
            job_id=row["id"],
            status=JobStatus(row["status"]),
            progress=row["progress"],
            message=row["message"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            url=row["url"],
            metadata=metadata,
            options=options,
            highlights=highlights,
            clips=clips,
            error=row["error"],
        )
    finally:
        await db.close()


async def update_job_status(
    job_id: str,
    status: JobStatus,
    progress: float = 0.0,
    message: str = "",
    error: Optional[str] = None,
) -> None:
    """Update job status and progress."""
    now = datetime.now(timezone.utc).isoformat()
    db = await _get_db()
    try:
        await db.execute(
            """UPDATE jobs SET status = ?, progress = ?, message = ?, error = ?, updated_at = ?
               WHERE id = ?""",
            (status.value, progress, message, error, now, job_id),
        )
        await db.commit()
    finally:
        await db.close()


async def update_job_metadata(job_id: str, metadata: JobMetadata) -> None:
    """Store video metadata for a job."""
    now = datetime.now(timezone.utc).isoformat()
    db = await _get_db()
    try:
        await db.execute(
            "UPDATE jobs SET metadata_json = ?, updated_at = ? WHERE id = ?",
            (metadata.model_dump_json(), now, job_id),
        )
        await db.commit()
    finally:
        await db.close()


# ── Highlight CRUD ─────────────────────────────────────────────

async def save_highlights(job_id: str, highlights: list[Highlight]) -> None:
    """Save detected highlights for a job."""
    db = await _get_db()
    try:
        for h in highlights:
            await db.execute(
                """INSERT OR REPLACE INTO highlights
                   (id, job_id, start_time, end_time, score, highlight_type, description,
                    transcript_snippet, chat_intensity, audio_energy, keyword_score, contributing_signals)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    h.id,
                    job_id,
                    h.start_time,
                    h.end_time,
                    h.score,
                    h.highlight_type.value,
                    h.description,
                    h.transcript_snippet,
                    h.chat_intensity,
                    h.audio_energy,
                    h.keyword_score,
                    json.dumps(h.contributing_signals),
                ),
            )
        await db.commit()
    finally:
        await db.close()
    logger.info(f"Saved {len(highlights)} highlights for job {job_id}")


# ── Clip CRUD ──────────────────────────────────────────────────

async def save_clip(job_id: str, clip: ClipInfo) -> None:
    """Save a generated clip record."""
    db = await _get_db()
    try:
        await db.execute(
            """INSERT OR REPLACE INTO clips
               (id, job_id, highlight_id, aspect_ratio, file_path, download_url,
                thumbnail_url, duration, has_subtitles)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                clip.id,
                job_id,
                clip.highlight_id,
                clip.aspect_ratio.value,
                clip.file_path,
                clip.download_url,
                clip.thumbnail_url,
                clip.duration,
                int(clip.has_subtitles),
            ),
        )
        await db.commit()
    finally:
        await db.close()


async def get_clip(job_id: str, clip_id: str) -> Optional[ClipInfo]:
    """Get a single clip by job_id and clip_id."""
    db = await _get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM clips WHERE id = ? AND job_id = ?", (clip_id, job_id)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return ClipInfo(
            id=row["id"],
            highlight_id=row["highlight_id"],
            aspect_ratio=AspectRatio(row["aspect_ratio"]),
            file_path=row["file_path"],
            download_url=row["download_url"],
            thumbnail_url=row["thumbnail_url"],
            duration=row["duration"],
            has_subtitles=bool(row["has_subtitles"]),
        )
    finally:
        await db.close()


async def list_jobs(limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
    """List all jobs (summary only)."""
    db = await _get_db()
    try:
        cursor = await db.execute(
            "SELECT id, url, status, progress, message, created_at, updated_at FROM jobs ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()
