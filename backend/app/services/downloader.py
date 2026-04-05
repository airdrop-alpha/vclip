"""
VClip downloader — yt-dlp based video download + audio extraction.
"""
from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yt_dlp

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class DownloadResult:
    """Result of a video download."""
    video_path: Path
    audio_path: Path
    title: str = ""
    channel: str = ""
    duration: float = 0.0
    upload_date: str = ""
    thumbnail_url: str = ""
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


def _progress_hook(d: dict[str, Any]) -> None:
    """Log download progress."""
    if d.get("status") == "downloading":
        pct = d.get("_percent_str", "?%")
        speed = d.get("_speed_str", "?")
        logger.debug(f"Download progress: {pct} at {speed}")
    elif d.get("status") == "finished":
        logger.info(f"Download finished: {d.get('filename', '?')}")


def extract_metadata(url: str) -> dict[str, Any]:
    """Extract video metadata without downloading."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info or {}


def _validate_job_id(job_id: str) -> None:
    """Ensure job_id is a safe hex string (no path traversal)."""
    if not job_id or not all(c in "0123456789abcdef" for c in job_id):
        raise ValueError(f"Invalid job_id: {job_id}")


def download_video(url: str, job_id: str) -> DownloadResult:
    """
    Download video from YouTube URL + extract audio as 16kHz mono WAV.

    Args:
        url: YouTube video URL
        job_id: Job ID for organizing temp files

    Returns:
        DownloadResult with paths to video and audio files plus metadata.
    """
    _validate_job_id(job_id)
    job_dir = settings.temp_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    video_path = job_dir / "video.mp4"
    audio_path = job_dir / "audio.wav"

    logger.info(f"[{job_id}] Downloading video from {url}")

    # Download video
    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": str(video_path),
        "merge_output_format": "mp4",
        "quiet": False,
        "no_warnings": False,
        "progress_hooks": [_progress_hook],
        # Don't download very high res for clipping purposes
        "format_sort": ["res:1080"],
        "max_filesize": 2 * 1024 * 1024 * 1024,  # 2 GB max
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    if info is None:
        raise RuntimeError(f"Failed to download video from {url}")

    # The actual output path may differ from the template
    # yt-dlp may add extensions or rename — find the actual file
    actual_video = _find_downloaded_file(job_dir, "video")
    if actual_video:
        video_path = actual_video

    if not video_path.exists():
        raise FileNotFoundError(f"Downloaded video not found at {video_path}")

    logger.info(f"[{job_id}] Video saved to {video_path} ({video_path.stat().st_size / 1e6:.1f} MB)")

    # Extract audio as 16kHz mono WAV for Whisper
    logger.info(f"[{job_id}] Extracting audio to WAV 16kHz mono")
    _extract_audio(video_path, audio_path)

    if not audio_path.exists():
        raise FileNotFoundError(f"Audio extraction failed — {audio_path} not found")

    logger.info(f"[{job_id}] Audio saved to {audio_path} ({audio_path.stat().st_size / 1e6:.1f} MB)")

    return DownloadResult(
        video_path=video_path,
        audio_path=audio_path,
        title=info.get("title", ""),
        channel=info.get("channel", info.get("uploader", "")),
        duration=float(info.get("duration", 0)),
        upload_date=info.get("upload_date", ""),
        thumbnail_url=info.get("thumbnail", ""),
        description=info.get("description", ""),
        metadata={
            "view_count": info.get("view_count"),
            "like_count": info.get("like_count"),
            "is_live": info.get("is_live", False),
            "was_live": info.get("was_live", False),
        },
    )


def _extract_audio(video_path: Path, audio_path: Path) -> None:
    """Extract audio from video as 16kHz mono WAV using ffmpeg."""
    cmd = [
        "ffmpeg",
        "-i", str(video_path),
        "-vn",                  # no video
        "-acodec", "pcm_s16le", # 16-bit PCM
        "-ar", "16000",         # 16kHz sample rate
        "-ac", "1",             # mono
        "-y",                   # overwrite
        str(audio_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        logger.error(f"ffmpeg audio extraction failed: {result.stderr[-500:]}")
        raise RuntimeError(f"Audio extraction failed: {result.stderr[-200:]}")


def _find_downloaded_file(directory: Path, prefix: str) -> Optional[Path]:
    """Find a downloaded file in the directory matching the prefix."""
    for ext in [".mp4", ".mkv", ".webm", ".mp4.part"]:
        candidate = directory / f"{prefix}{ext}"
        if candidate.exists():
            return candidate
    # Glob fallback
    candidates = list(directory.glob(f"{prefix}*"))
    video_exts = {".mp4", ".mkv", ".webm"}
    for c in candidates:
        if c.suffix in video_exts:
            return c
    return None
