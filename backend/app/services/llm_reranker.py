"""
VClip LLM re-ranker — re-rank and annotate highlights using an LLM.

Uses OpenAI API (or compatible) to score and explain detected highlights
in the context of VTuber content. Falls back gracefully to the original
signal-based scores when the API is unavailable or not configured.

Phase 3 feature.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from app.config import settings
from app.models import Highlight, HighlightType

logger = logging.getLogger(__name__)


# ── Prompt templates ──────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a VTuber clip editor assistant. Your job is to evaluate detected
highlight moments from VTuber livestreams and rank them by entertainment/shareability value.

For each highlight, you receive:
- Transcript snippet (what was said)
- Detection signals: chat activity, audio energy, keyword matches
- Time range

You must return a JSON array with one object per highlight (same order as input):
{
  "rank": <1-indexed integer rank, 1 = best>,
  "confidence": <float 0.0-1.0, your confidence in this being a good clip>,
  "explanation": <1-2 sentence explanation of why this moment is notable>,
  "highlight_type": <"funny"|"exciting"|"emotional"|"skill"|"mixed">
}

Focus on: humor, genuine reactions, impressive gameplay, emotional moments, meme-worthy content.
Be concise. Return ONLY the JSON array."""


def _build_user_prompt(highlights: list[Highlight]) -> str:
    """Build the user prompt from highlight data."""
    lines = [f"Evaluate these {len(highlights)} highlight moments:\n"]
    for i, h in enumerate(highlights, 1):
        duration = h.end_time - h.start_time
        lines.append(
            f"[{i}] {int(h.start_time//60)}:{int(h.start_time%60):02d}–"
            f"{int(h.end_time//60)}:{int(h.end_time%60):02d} "
            f"({duration:.0f}s)\n"
            f"  Transcript: {h.transcript_snippet[:200] or '(no transcript)'}\n"
            f"  Signals: chat={h.chat_intensity:.2f} audio={h.audio_energy:.2f} "
            f"keywords={h.keyword_score:.2f}\n"
            f"  Existing type: {h.highlight_type.value}\n"
        )
    return "\n".join(lines)


def _mock_rerank(highlights: list[Highlight]) -> list[Highlight]:
    """
    Mock re-ranker used when OpenAI is not configured.

    Applies a simple heuristic boost based on chat + keyword signals
    and adds placeholder explanations.
    """
    logger.info("LLM re-ranking: using mock mode (OPENAI_API_KEY not set)")

    type_labels = {
        HighlightType.FUNNY: "funny moment with high viewer engagement",
        HighlightType.EXCITING: "exciting moment with chat spike",
        HighlightType.EMOTIONAL: "emotional moment that resonated with viewers",
        HighlightType.SKILL: "impressive skill display",
        HighlightType.MIXED: "notable moment with mixed signals",
    }

    scored = []
    for h in highlights:
        # Composite boost: weight chat more for entertainment
        boost = 0.6 * h.chat_intensity + 0.25 * h.audio_energy + 0.15 * h.keyword_score
        explanation = (
            f"Auto-detected {type_labels.get(h.highlight_type, 'notable moment')} "
            f"(chat={h.chat_intensity:.2f}, audio={h.audio_energy:.2f})."
        )
        scored.append((h, boost, explanation))

    # Sort by boost score descending
    scored.sort(key=lambda x: x[1], reverse=True)

    result = []
    for rank, (h, boost, explanation) in enumerate(scored, 1):
        updated = h.model_copy(update={
            "llm_rank": rank,
            "confidence": round(min(boost, 1.0), 4),
            "llm_explanation": explanation,
        })
        result.append(updated)

    # Re-sort by llm_rank
    result.sort(key=lambda x: x.llm_rank or 99)
    return result


def rerank_highlights(
    highlights: list[Highlight],
    video_title: str = "",
    channel: str = "",
) -> list[Highlight]:
    """
    Re-rank highlights using LLM scoring.

    If OPENAI_API_KEY is set and llm_rerank_enabled=true, calls the OpenAI
    API to score and explain each highlight. Falls back to mock scoring otherwise.

    Args:
        highlights: Detected highlights (signal-scored)
        video_title: Video title for context
        channel: Channel name for context

    Returns:
        Highlights sorted by LLM rank (best first), with llm_explanation and
        confidence fields populated.
    """
    if not highlights:
        return highlights

    if not settings.llm_rerank_enabled or not settings.openai_api_key:
        return _mock_rerank(highlights)

    try:
        return _openai_rerank(highlights, video_title, channel)
    except Exception as e:
        logger.warning(f"LLM re-ranking failed, falling back to mock: {e}")
        return _mock_rerank(highlights)


def _openai_rerank(
    highlights: list[Highlight],
    video_title: str,
    channel: str,
) -> list[Highlight]:
    """Call OpenAI API to re-rank highlights."""
    try:
        import openai  # type: ignore
    except ImportError:
        raise RuntimeError("openai package not installed; run: pip install openai")

    client = openai.OpenAI(api_key=settings.openai_api_key)

    context_note = ""
    if video_title or channel:
        context_note = f"\nVideo: {video_title!r} by {channel}\n"

    user_prompt = context_note + _build_user_prompt(highlights)

    logger.info(
        f"LLM re-ranking {len(highlights)} highlights via {settings.openai_model}"
    )

    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=1024,
        response_format={"type": "json_object"} if "gpt-4" in settings.openai_model else None,
    )

    raw = response.choices[0].message.content or "[]"

    # Parse JSON — handle both array and {"highlights": [...]}
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            parsed = parsed.get("highlights", parsed.get("results", list(parsed.values())[0]))
        if not isinstance(parsed, list):
            raise ValueError("Expected JSON array")
    except (json.JSONDecodeError, ValueError, IndexError) as e:
        raise RuntimeError(f"LLM returned invalid JSON: {e}\nRaw: {raw[:200]}")

    # Map results back to highlights
    result = list(highlights)
    for i, item in enumerate(parsed):
        if i >= len(result):
            break
        h = result[i]
        try:
            hl_type_str = item.get("highlight_type", h.highlight_type.value)
            try:
                hl_type = HighlightType(hl_type_str)
            except ValueError:
                hl_type = h.highlight_type

            result[i] = h.model_copy(update={
                "llm_rank": int(item.get("rank", i + 1)),
                "confidence": float(item.get("confidence", h.score)),
                "llm_explanation": str(item.get("explanation", "")),
                "highlight_type": hl_type,
            })
        except (TypeError, ValueError) as e:
            logger.debug(f"Failed to parse LLM result for highlight {i}: {e}")

    # Sort by LLM rank
    result.sort(key=lambda x: x.llm_rank or 99)
    logger.info(f"LLM re-ranking complete: {len(result)} highlights re-ranked")
    return result
