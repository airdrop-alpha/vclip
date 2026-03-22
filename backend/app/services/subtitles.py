"""
VClip subtitle generator — ASS format with anime-style styling.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from app.config import settings
from app.models import SubtitleStyle, TranscriptSegment, WordTimestamp

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════
#  ASS STYLE PRESETS
# ══════════════════════════════════════════════════════════════════

ASS_STYLES: dict[SubtitleStyle, dict] = {
    SubtitleStyle.ANIME: {
        "fontname": "Arial",
        "fontsize": 48,
        "primary_color": "&H00FFFFFF",    # White
        "secondary_color": "&H000088FF",  # Orange accent
        "outline_color": "&H00000000",    # Black outline
        "back_color": "&H80000000",       # Semi-transparent background
        "bold": -1,
        "outline": 3,
        "shadow": 1,
        "alignment": 2,  # Bottom center
        "margin_v": 40,
        "border_style": 1,
    },
    SubtitleStyle.MODERN: {
        "fontname": "Helvetica Neue",
        "fontsize": 44,
        "primary_color": "&H00FFFFFF",
        "secondary_color": "&H0000AAFF",
        "outline_color": "&H40000000",
        "back_color": "&H80000000",
        "bold": 0,
        "outline": 2,
        "shadow": 0,
        "alignment": 2,
        "margin_v": 30,
        "border_style": 3,  # Opaque box
    },
    SubtitleStyle.MINIMAL: {
        "fontname": "Arial",
        "fontsize": 40,
        "primary_color": "&H00FFFFFF",
        "secondary_color": "&H00FFFFFF",
        "outline_color": "&H60000000",
        "back_color": "&H00000000",
        "bold": 0,
        "outline": 1,
        "shadow": 0,
        "alignment": 2,
        "margin_v": 25,
        "border_style": 1,
    },
}


# ══════════════════════════════════════════════════════════════════
#  ASS FILE GENERATION
# ══════════════════════════════════════════════════════════════════

def generate_ass(
    segments: list[TranscriptSegment],
    output_path: Path,
    style: SubtitleStyle = SubtitleStyle.ANIME,
    clip_start: float = 0.0,
    clip_end: Optional[float] = None,
    video_width: int = 1920,
    video_height: int = 1080,
) -> Path:
    """
    Generate an ASS subtitle file from transcript segments.

    Args:
        segments: Transcript segments with word-level timestamps
        output_path: Where to save the ASS file
        style: Visual style preset
        clip_start: Start time of the clip (for offsetting timestamps)
        clip_end: End time of the clip
        video_width: Target video width
        video_height: Target video height

    Returns:
        Path to the generated ASS file.
    """
    style_config = ASS_STYLES.get(style, ASS_STYLES[SubtitleStyle.ANIME])

    # Filter segments to clip range
    relevant_segments = []
    for seg in segments:
        if clip_end and seg.start > clip_end:
            break
        if seg.end >= clip_start:
            relevant_segments.append(seg)

    lines: list[str] = []

    # ASS header
    lines.append("[Script Info]")
    lines.append("Title: VClip Subtitles")
    lines.append("ScriptType: v4.00+")
    lines.append(f"PlayResX: {video_width}")
    lines.append(f"PlayResY: {video_height}")
    lines.append("WrapStyle: 0")
    lines.append("ScaledBorderAndShadow: yes")
    lines.append("")

    # Styles
    lines.append("[V4+ Styles]")
    lines.append(
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding"
    )
    lines.append(
        f"Style: Default,{style_config['fontname']},{style_config['fontsize']},"
        f"{style_config['primary_color']},{style_config['secondary_color']},"
        f"{style_config['outline_color']},{style_config['back_color']},"
        f"{style_config['bold']},0,0,0,"
        f"100,100,0,0,"
        f"{style_config['border_style']},{style_config['outline']},{style_config['shadow']},"
        f"{style_config['alignment']},20,20,{style_config['margin_v']},1"
    )
    lines.append("")

    # Events
    lines.append("[Events]")
    lines.append("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text")

    for seg in relevant_segments:
        # Offset times relative to clip start
        seg_start = max(0.0, seg.start - clip_start)
        seg_end = seg.end - clip_start

        if clip_end:
            seg_end = min(seg_end, clip_end - clip_start)

        if seg_end <= seg_start:
            continue

        # Format text — add word-by-word karaoke effect for anime style
        if style == SubtitleStyle.ANIME and seg.words:
            text = _build_karaoke_text(seg.words, clip_start)
        else:
            text = seg.text.strip()

        # Escape ASS special characters
        text = text.replace("\\", "\\\\")

        start_str = _format_ass_time(seg_start)
        end_str = _format_ass_time(seg_end)

        lines.append(
            f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,"
            f"{text}"
        )

    # Write file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines))

    logger.info(f"Generated ASS subtitles: {output_path} ({len(relevant_segments)} segments)")
    return output_path


def _build_karaoke_text(words: list[WordTimestamp], clip_start: float) -> str:
    """
    Build karaoke-style ASS text with word-by-word highlight timing.

    Uses the \\k tag for karaoke timing (in centiseconds).
    """
    parts: list[str] = []
    for word in words:
        # Duration in centiseconds (ASS karaoke unit)
        dur_cs = max(1, int((word.end - word.start) * 100))
        w = word.word.strip()
        if w:
            parts.append(f"{{\\kf{dur_cs}}}{w}")
    return "".join(parts)


def _format_ass_time(seconds: float) -> str:
    """Format seconds to ASS timestamp: H:MM:SS.cc"""
    if seconds < 0:
        seconds = 0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


# ══════════════════════════════════════════════════════════════════
#  BATCH SUBTITLE GENERATION
# ══════════════════════════════════════════════════════════════════

def generate_subtitles_for_highlights(
    transcript: list[TranscriptSegment],
    highlights: list,
    job_id: str,
    style: SubtitleStyle = SubtitleStyle.ANIME,
) -> dict[str, Path]:
    """
    Generate ASS subtitle files for each highlight.

    Args:
        transcript: Full transcript with word-level timestamps
        highlights: List of Highlight objects
        job_id: Job ID for file organization
        style: Subtitle style preset

    Returns:
        Dict mapping highlight_id -> Path to ASS file.
    """
    sub_dir = settings.clips_dir / job_id / "subs"
    sub_dir.mkdir(parents=True, exist_ok=True)

    subtitle_paths: dict[str, Path] = {}

    for highlight in highlights:
        output_path = sub_dir / f"sub_{highlight.id}.ass"

        try:
            generate_ass(
                segments=transcript,
                output_path=output_path,
                style=style,
                clip_start=highlight.start_time,
                clip_end=highlight.end_time,
            )
            subtitle_paths[highlight.id] = output_path
        except Exception as e:
            logger.error(f"Failed to generate subtitles for highlight {highlight.id}: {e}")

    logger.info(f"Generated {len(subtitle_paths)} subtitle files for job {job_id}")
    return subtitle_paths
