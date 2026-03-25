"""
VClip clip routes — download and export generated clips.
"""
from __future__ import annotations

import io
import logging
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from app.config import settings
from app.db import get_clip, get_job

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/jobs/{job_id}/clips", tags=["clips"])


@router.get("/{clip_id}/download")
async def download_clip(job_id: str, clip_id: str):
    """
    Download a single generated clip.

    Returns the MP4 file as a streaming download.
    """
    clip = await get_clip(job_id, clip_id)
    if clip is None:
        raise HTTPException(status_code=404, detail=f"Clip {clip_id} not found in job {job_id}")

    file_path = Path(clip.file_path).resolve()
    clips_root = settings.clips_dir.resolve()
    if not str(file_path).startswith(str(clips_root)):
        raise HTTPException(status_code=403, detail="Access denied")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Clip file not found on disk")

    return FileResponse(
        path=str(file_path),
        media_type="video/mp4",
        filename=f"vclip_{job_id}_{clip_id}.mp4",
        headers={
            "Content-Disposition": f'attachment; filename="vclip_{job_id}_{clip_id}.mp4"'
        },
    )


# Export route is on the job level, not clip level
export_router = APIRouter(prefix="/api/v1/jobs/{job_id}", tags=["export"])


@export_router.get("/export")
async def export_all_clips(job_id: str):
    """
    Export all clips for a job as a ZIP archive.

    Streams the ZIP file without writing to disk.
    """
    job = await get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if not job.clips:
        raise HTTPException(status_code=404, detail="No clips available for this job")

    # Build ZIP in memory
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, clip in enumerate(job.clips):
            file_path = Path(clip.file_path).resolve()
            clips_root = settings.clips_dir.resolve()
            if not str(file_path).startswith(str(clips_root)):
                continue
            if file_path.exists():
                # Name clips sequentially with aspect ratio label
                ratio_label = "landscape" if clip.aspect_ratio.value == "16:9" else "portrait"
                arc_name = f"clip_{i+1:02d}_{ratio_label}.mp4"
                zf.write(file_path, arc_name)
                logger.debug(f"Added {arc_name} to zip")
            else:
                logger.warning(f"Clip file not found: {file_path}")

    zip_buffer.seek(0)
    zip_size = zip_buffer.getbuffer().nbytes

    if zip_size <= 22:  # Empty ZIP header size
        raise HTTPException(status_code=404, detail="No clip files found on disk")

    title_slug = "".join(c if c.isalnum() or c in "-_" else "_" for c in (job.metadata.title if job.metadata else job_id)[:40])
    filename = f"vclip_{title_slug}.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(zip_size),
        },
    )
