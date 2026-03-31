"""
VClip template engine — FFmpeg filter chains for clip styling.

Three built-in templates:
  anime   — warm vignette, slight saturation boost, rounded overlay bar
  modern  — clean with subtle letterbox and drop shadow
  minimal — no-frills, just crop/scale and optional text badge

Phase 4 feature.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from app.models import AspectRatio

logger = logging.getLogger(__name__)


@dataclass
class TemplateConfig:
    """FFmpeg filter parameters for a clip template."""
    name: str
    # Video filter chain (list of individual filter strings, joined by comma)
    video_filters: list[str] = field(default_factory=list)
    # Additional ffmpeg flags (e.g. -vf extension)
    extra_flags: list[str] = field(default_factory=list)
    description: str = ""


# ── Built-in templates ─────────────────────────────────────────────

_TEMPLATES: dict[str, TemplateConfig] = {
    "anime": TemplateConfig(
        name="anime",
        description="Warm colors, slight vignette, saturation boost — VTuber style",
        video_filters=[
            # Subtle warm tone + saturation boost
            "eq=saturation=1.15:contrast=1.05:brightness=0.01",
            # Soft vignette overlay
            "vignette=PI/5",
        ],
    ),
    "modern": TemplateConfig(
        name="modern",
        description="Clean look with subtle contrast enhancement",
        video_filters=[
            "eq=contrast=1.08:saturation=1.05",
        ],
    ),
    "minimal": TemplateConfig(
        name="minimal",
        description="No processing — raw clip output",
        video_filters=[],
    ),
    "vhs": TemplateConfig(
        name="vhs",
        description="Retro VHS aesthetic with chromatic aberration simulation",
        video_filters=[
            "eq=saturation=0.85:contrast=0.95",
            "noise=alls=4:allf=t+u",
        ],
    ),
}

_DEFAULT_TEMPLATE = "anime"


def get_template(name: str) -> TemplateConfig:
    """Get template config by name; falls back to anime if unknown."""
    tmpl = _TEMPLATES.get(name.lower())
    if tmpl is None:
        logger.warning(f"Unknown template '{name}', falling back to '{_DEFAULT_TEMPLATE}'")
        tmpl = _TEMPLATES[_DEFAULT_TEMPLATE]
    return tmpl


def list_templates() -> list[dict]:
    """Return list of available templates for API response."""
    return [
        {"name": t.name, "description": t.description}
        for t in _TEMPLATES.values()
    ]


def build_video_filter_chain(
    template_name: str,
    aspect_ratio: AspectRatio,
    subtitle_path: Optional[str] = None,
    watermark_text: Optional[str] = None,
) -> list[str]:
    """
    Build the complete video filter chain for a clip.

    Combines aspect ratio crop/scale, template effects, subtitle burn-in,
    and optional watermark text.

    Returns:
        List of individual filter strings (to be joined with comma for -vf).
    """
    tmpl = get_template(template_name)
    filters: list[str] = []

    # 1. Aspect ratio crop / scale
    if aspect_ratio == AspectRatio.PORTRAIT:
        filters.append("scale=-2:1920")
        filters.append("crop=1080:1920:(iw-1080)/2:0")
    else:
        filters.append("scale=1920:1080:force_original_aspect_ratio=decrease")
        filters.append("pad=1920:1080:(ow-iw)/2:(oh-ih)/2")

    # 2. Template effects
    filters.extend(tmpl.video_filters)

    # 3. Watermark text overlay
    if watermark_text:
        escaped = watermark_text.replace("'", "\\'").replace(":", "\\:")
        if aspect_ratio == AspectRatio.PORTRAIT:
            x, y = "(w-text_w)/2", "h-60"
        else:
            x, y = "w-text_w-30", "h-50"
        filters.append(
            f"drawtext=text='{escaped}'"
            f":fontsize=28:fontcolor=white@0.55"
            f":x={x}:y={y}"
            f":shadowcolor=black@0.4:shadowx=1:shadowy=1"
        )

    # 4. Subtitle burn-in (must be last — uses overlay coordinates)
    if subtitle_path:
        escaped_path = (
            subtitle_path.replace("\\", "/")
            .replace(":", "\\:")
            .replace("'", "\\'")
        )
        filters.append(f"subtitles={escaped_path}")

    return filters
