"""
VClip chat parser — extract YouTube live chat replay messages.

Uses yt-dlp to download live chat replay data from YouTube VODs
that were originally livestreamed.
"""
from __future__ import annotations

import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from app.models import ChatMessage

logger = logging.getLogger(__name__)


def parse_live_chat(url: str, job_id: str = "") -> list[ChatMessage]:
    """
    Extract live chat replay from a YouTube video URL.

    Uses yt-dlp to download the live chat JSON, then parses it into
    timestamped ChatMessage objects.

    Args:
        url: YouTube video URL
        job_id: Job ID for logging context

    Returns:
        List of ChatMessage sorted by timestamp.
        Returns empty list if the video wasn't a livestream or has no chat.
    """
    logger.info(f"[{job_id}] Parsing live chat for {url}")

    try:
        messages = _download_chat_yt_dlp(url)
    except Exception as e:
        logger.warning(f"[{job_id}] Could not extract live chat: {e}")
        logger.info(f"[{job_id}] Video may not be a livestream — returning empty chat")
        return []

    if not messages:
        logger.info(f"[{job_id}] No chat messages found")
        return []

    # Sort by timestamp
    messages.sort(key=lambda m: m.timestamp)
    logger.info(f"[{job_id}] Parsed {len(messages)} chat messages")

    return messages


def _download_chat_yt_dlp(url: str) -> list[ChatMessage]:
    """
    Download live chat using yt-dlp's --write-subs with live_chat format.

    yt-dlp saves live chat as a JSON lines file (.live_chat.json).
    """
    with tempfile.TemporaryDirectory(prefix="vclip_chat_") as tmpdir:
        output_template = str(Path(tmpdir) / "chat")

        cmd = [
            "yt-dlp",
            "--skip-download",
            "--write-subs",
            "--sub-langs", "live_chat",
            "--output", output_template,
            url,
        ]

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120
        )

        if result.returncode != 0:
            # Check for common "no live chat" scenarios
            stderr = result.stderr.lower()
            if "no subtitles" in stderr or "live_chat" in stderr:
                logger.debug("No live chat subtitles available")
                return []
            raise RuntimeError(f"yt-dlp chat extraction failed: {result.stderr[-300:]}")

        # Find the downloaded chat file
        chat_files = list(Path(tmpdir).glob("*.live_chat.json"))
        if not chat_files:
            logger.debug("No live_chat.json file produced")
            return []

        return _parse_chat_json(chat_files[0])


def _parse_chat_json(chat_path: Path) -> list[ChatMessage]:
    """
    Parse yt-dlp's live_chat.json (JSON Lines format).

    Each line is a JSON object representing a chat action.
    We extract text messages and super chat events.
    """
    messages: list[ChatMessage] = []

    with open(chat_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f):
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg = _extract_message(data)
            if msg is not None:
                messages.append(msg)

            if line_num % 10000 == 0 and line_num > 0:
                logger.debug(f"Parsed {line_num} chat lines, {len(messages)} messages extracted")

    return messages


def _extract_message(data: dict) -> Optional[ChatMessage]:
    """
    Extract a ChatMessage from a yt-dlp live chat JSON action.

    Handles both regular messages and super chats.
    """
    # yt-dlp live chat format wraps actions in replayChatItemAction
    replay_action = data.get("replayChatItemAction", {})
    actions = replay_action.get("actions", [])

    for action in actions:
        item = action.get("addChatItemAction", {}).get("item", {})

        # Regular text message
        renderer = item.get("liveChatTextMessageRenderer")
        if renderer:
            return _parse_text_message(renderer, data)

        # Super chat / super sticker
        renderer = item.get("liveChatPaidMessageRenderer")
        if renderer:
            return _parse_superchat(renderer, data)

    return None


def _parse_text_message(renderer: dict, root: dict) -> Optional[ChatMessage]:
    """Parse a regular live chat text message."""
    text = _extract_text_runs(renderer.get("message", {}))
    if not text:
        return None

    author = _extract_text_runs(renderer.get("authorName", {}))
    timestamp = _get_timestamp_seconds(root)

    if timestamp is None:
        return None

    # Check membership badge
    is_member = bool(renderer.get("authorBadges"))

    return ChatMessage(
        timestamp=timestamp,
        author=author,
        message=text,
        is_member=is_member,
        is_superchat=False,
    )


def _parse_superchat(renderer: dict, root: dict) -> Optional[ChatMessage]:
    """Parse a super chat message."""
    text = _extract_text_runs(renderer.get("message", {}))
    header_text = renderer.get("headerSubtext", {})
    if not text:
        text = _extract_text_runs(header_text) or "[Super Chat]"

    author = _extract_text_runs(renderer.get("authorName", {}))
    timestamp = _get_timestamp_seconds(root)

    if timestamp is None:
        return None

    # Extract amount
    amount_text = renderer.get("purchaseAmountText", {}).get("simpleText", "")
    amount = _parse_amount(amount_text)

    return ChatMessage(
        timestamp=timestamp,
        author=author,
        message=text,
        is_member=True,
        is_superchat=True,
        amount=amount,
    )


def _extract_text_runs(message_obj: dict) -> str:
    """Extract text from YouTube's 'runs' format."""
    if not message_obj:
        return ""

    # Simple text
    if "simpleText" in message_obj:
        return message_obj["simpleText"]

    # Runs (mixed text + emoji)
    runs = message_obj.get("runs", [])
    parts = []
    for run in runs:
        if "text" in run:
            parts.append(run["text"])
        elif "emoji" in run:
            # Use emoji shortcut text or unicode
            emoji = run["emoji"]
            shortcuts = emoji.get("shortcuts", [])
            if shortcuts:
                parts.append(shortcuts[0])
            else:
                eid = emoji.get("emojiId", "")
                parts.append(eid if eid else "🎭")
    return "".join(parts)


def _get_timestamp_seconds(data: dict) -> Optional[float]:
    """
    Get the video-relative timestamp in seconds.

    yt-dlp provides videoOffsetTimeMsec in replayChatItemAction.
    """
    replay = data.get("replayChatItemAction", {})

    # videoOffsetTimeMsec — milliseconds from video start
    offset_ms = replay.get("videoOffsetTimeMsec")
    if offset_ms is not None:
        try:
            return int(offset_ms) / 1000.0
        except (ValueError, TypeError):
            pass

    return None


def _parse_amount(amount_text: str) -> Optional[float]:
    """Parse a currency amount string like '$5.00' or '¥500'."""
    if not amount_text:
        return None
    # Strip common currency symbols
    cleaned = amount_text.replace("$", "").replace("¥", "").replace("€", "").replace("£", "")
    cleaned = cleaned.replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None
