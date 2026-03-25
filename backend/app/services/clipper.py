"""
VClip clipper — FFmpeg-based clip extraction from source video.
"""
from __future__ import annotations

import logging
import subprocess
import uuid
from pathlib import Path

from app.config import settings
from app.models import AspectRatio, ClipInfo, Highlight

logger = logging.getLogger(__name__)


def extract_clip(
    video_path: Path,
    highlight: Highlight,
    job_id: str,
    aspect_ratio: AspectRatio = AspectRatio.LANDSCAPE,
    buffer: int | None = None,
    subtitle_path: Path | None = None,
) -> ClipInfo:
    """
    Extract a clip from the source video at the highlight's timestamps.

    Args:
        video_path: Path to the full source video
        highlight: Highlight with start_time and end_time
        job_id: Job ID for organizing output files
        aspect_ratio: Output aspect ratio (16:9 or 9:16)
        buffer: Extra seconds of padding around the highlight (default: config)
        subtitle_path: Optional ASS subtitle file to burn in

    Returns:
        ClipInfo with the path to the generated clip.
    """
    if not job_id or not all(c in "0123456789abcdef" for c in job_id):
        raise ValueError(f"Invalid job_id: {job_id}")
    buf = buffer if buffer is not None else settings.highlight_buffer
    clip_id = uuid.uuid4().hex[:12]

    # Calculate actual clip boundaries with buffer
    start = max(0.0, highlight.start_time - buf)
    end = highlight.end_time + buf
    duration = end - start

    # Output path
    clip_dir = settings.clips_dir / job_id
    clip_dir.mkdir(parents=True, exist_ok=True)

    ratio_label = "landscape" if aspect_ratio == AspectRatio.LANDSCAPE else "portrait"
    output_path = clip_dir / f"clip_{clip_id}_{ratio_label}.mp4"

    logger.info(
        f"[{job_id}] Extracting clip {clip_id}: "
        f"{start:.1f}s–{end:.1f}s ({duration:.1f}s), "
        f"aspect={aspect_ratio.value}"
    )

    # Build ffmpeg command
    cmd = _build_ffmpeg_cmd(
        video_path=video_path,
        output_path=output_path,
        start=start,
        duration=duration,
        aspect_ratio=aspect_ratio,
        subtitle_path=subtitle_path,
    )

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        logger.error(f"FFmpeg clip extraction failed: {result.stderr[-500:]}")
        raise RuntimeError(f"Clip extraction failed: {result.stderr[-200:]}")

    if not output_path.exists():
        raise FileNotFoundError(f"Output clip not found at {output_path}")

    file_size = output_path.stat().st_size / 1e6
    logger.info(f"[{job_id}] Clip saved: {output_path} ({file_size:.1f} MB)")

    return ClipInfo(
        id=clip_id,
        highlight_id=highlight.id,
        aspect_ratio=aspect_ratio,
        file_path=str(output_path),
        download_url=f"/api/v1/jobs/{job_id}/clips/{clip_id}/download",
        duration=duration,
        has_subtitles=subtitle_path is not None,
    )


def _build_ffmpeg_cmd(
    video_path: Path,
    output_path: Path,
    start: float,
    duration: float,
    aspect_ratio: AspectRatio,
    subtitle_path: Path | None = None,
) -> list[str]:
    """Build the ffmpeg command for clip extraction."""
    cmd = [
        "ffmpeg",
        "-ss", str(start),
        "-i", str(video_path),
        "-t", str(duration),
    ]

    # Build filter chain
    filters: list[str] = []

    if aspect_ratio == AspectRatio.PORTRAIT:
        # 9:16 center crop from 16:9 source
        # First scale to ensure minimum height, then crop center
        filters.append("scale=-2:1920")
        filters.append("crop=1080:1920:(iw-1080)/2:0")
    else:
        # 16:9 — scale to 1920x1080 if needed
        filters.append("scale=1920:1080:force_original_aspect_ratio=decrease")
        filters.append("pad=1920:1080:(ow-iw)/2:(oh-ih)/2")

    # Burn in subtitles if provided
    if subtitle_path and subtitle_path.exists():
        # ASS subtitles via the subtitles filter
        # FFmpeg filter escaping: backslash-escape special chars, no surrounding quotes
        escaped_path = str(subtitle_path.resolve()).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
        filters.append(f"subtitles={escaped_path}")

    if filters:
        cmd.extend(["-vf", ",".join(filters)])

    # Output codec settings
    cmd.extend([
        "-c:v", settings.video_codec,
        "-crf", str(settings.video_crf),
        "-preset", "medium",
        "-c:a", settings.audio_codec,
        "-b:a", settings.audio_bitrate,
        "-movflags", "+faststart",  # Web-optimized MP4
        "-y",
        str(output_path),
    ])

    return cmd


def extract_clips_batch(
    video_path: Path,
    highlights: list[Highlight],
    job_id: str,
    aspect_ratios: list[AspectRatio] | None = None,
    subtitle_paths: dict[str, Path] | None = None,
) -> list[ClipInfo]:
    """
    Extract clips for multiple highlights.

    Args:
        video_path: Source video path
        highlights: List of highlights to clip
        job_id: Job ID
        aspect_ratios: List of aspect ratios to generate per clip
        subtitle_paths: Map of highlight_id -> ASS subtitle path

    Returns:
        List of generated ClipInfo objects.
    """
    ratios = aspect_ratios or [AspectRatio.LANDSCAPE]
    sub_paths = subtitle_paths or {}
    clips: list[ClipInfo] = []

    for i, highlight in enumerate(highlights):
        for ratio in ratios:
            try:
                sub_path = sub_paths.get(highlight.id)
                clip = extract_clip(
                    video_path=video_path,
                    highlight=highlight,
                    job_id=job_id,
                    aspect_ratio=ratio,
                    subtitle_path=sub_path,
                )
                clips.append(clip)
                logger.info(
                    f"[{job_id}] Clip {i+1}/{len(highlights)} "
                    f"({ratio.value}) complete"
                )
            except Exception as e:
                logger.error(
                    f"[{job_id}] Failed to extract clip for highlight "
                    f"{highlight.id}: {e}"
                )

    return clips
