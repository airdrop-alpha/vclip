"""
VClip highlight detection engine — the CORE VALUE of the product.

Multi-signal highlight detection for VTuber streams:
  1. Chat spike detection (sliding window + z-score)
  2. Audio energy peaks (librosa RMS + z-score)
  3. Keyword triggers (VTuber-specific vocabulary)
  4. Composite scoring with weighted fusion
  5. Peak finding, merging, and sentence-boundary snapping
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
from scipy.signal import find_peaks as scipy_find_peaks

from app.config import settings
from app.models import (
    ChatMessage,
    Highlight,
    HighlightType,
    TranscriptSegment,
)

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════
#  KEYWORD DICTIONARY — VTuber-specific vocabulary (from PRD Appendix B)
# ══════════════════════════════════════════════════════════════════

KEYWORDS: dict[str, dict[str, list[str]]] = {
    # ── Japanese reactions ────────────────────────────────────
    "ja": {
        "excitement": [
            "草", "くさ", "wwww", "www", "ww",
            "ワロタ", "わろた",
            "やばい", "ヤバい", "ヤバイ",
            "すごい", "スゴイ", "すげー", "すげぇ",
            "まじ", "マジ", "まじか", "マジか",
            "うそ", "ウソ", "嘘",
            "えぇぇ", "えぇ", "ええ",
            "きたー", "キター", "きたあ",
            "おお", "おおお",
        ],
        "emotion": [
            "泣ける", "なける",
            "感動", "かんどう",
            "かわいい", "カワイイ", "可愛い",
            "尊い", "とうとい",
            "てぇてぇ", "テェテェ",
            "推せる", "おせる",
            "好き", "すき",
            "エモい", "えもい",
        ],
        "action": [
            "神プレイ", "かみプレイ",
            "ナイス", "ないす",
            "うまい", "ウマい", "上手い",
            "天才", "てんさい",
            "さすが", "サスガ", "流石",
            "神", "かみ",
            "プロ", "ぷろ",
            "完璧", "かんぺき",
        ],
        "surprise": [
            "!?", "！？",
            "えぇ", "ええ",
            "うわぁ", "うわあ", "うわー",
            "なにぃ", "なに", "何",
            "はぁ!?", "はぁ",
            "まって", "マッテ", "待って",
            "ちょっと", "チョット",
            "こわい", "怖い", "コワイ",
        ],
    },
    # ── English reactions ─────────────────────────────────────
    "en": {
        "excitement": [
            "LETS GO", "LET'S GO", "lets go", "let's go",
            "POG", "pog", "poggers", "POGGERS",
            "no way", "NO WAY",
            "omg", "OMG", "oh my god",
            "lol", "LOL", "lmao", "LMAO",
            "bruh", "BRUH",
            "hype", "HYPE",
            "sheesh", "SHEESH",
            "fire", "FIRE",
            "based", "BASED",
            "W", "huge W",
        ],
        "emotion": [
            "crying", "im crying", "i'm crying",
            "wholesome", "WHOLESOME",
            "cute", "CUTE", "so cute",
            "precious", "PRECIOUS",
            "beautiful",
            "aww", "AWW",
        ],
        "action": [
            "clutch", "CLUTCH",
            "insane", "INSANE",
            "cracked", "CRACKED",
            "goated", "GOATED",
            "god gamer", "god-gamer",
            "clean", "CLEAN",
            "gg", "GG",
            "ace", "ACE",
            "carry", "CARRY",
        ],
        "surprise": [
            "WHAT", "what",
            "HOW", "how",
            "wait what", "WAIT WHAT",
            "no shot", "NO SHOT",
            "yo", "YO",
            "oh no", "OH NO",
            "bro", "BRO",
            "nani", "NANI",
            "huh", "HUH",
        ],
    },
    # ── Chinese reactions ─────────────────────────────────────
    "zh": {
        "excitement": [
            "草", "草草草",
            "哈哈哈", "哈哈哈哈",
            "笑死", "笑死了",
            "666", "6666", "66666",
            "牛逼", "牛b", "nb", "NB",
            "太强了", "太強了",
            "绝了", "絕了",
            "真的假的",
            "爆笑",
        ],
        "emotion": [
            "好可爱", "好可愛",
            "泪目", "淚目",
            "感动", "感動",
            "贴贴", "貼貼",
            "好甜", "甜死了",
            "心疼",
            "破防了",
        ],
        "action": [
            "神操作",
            "厉害", "厲害",
            "太猛了",
            "秀", "秀啊",
            "大佬", "大神",
            "高手",
            "666操作",
        ],
        "surprise": [
            "卧槽", "臥槽",
            "我靠",
            "什么鬼", "什麼鬼",
            "不会吧", "不會吧",
            "啊这", "啊這",
            "离谱", "離譜",
            "震惊", "震驚",
        ],
    },
    # ── Universal emotes (Twitch/YouTube) ─────────────────────
    "emotes": {
        "positive": [
            "PogChamp", "KEKW", "Pog", "catJAM", "HYPERS",
            "PepeHands", "OMEGALUL", "monkaW", "EZ",
            "PogU", "Clap", "HypeChamp",
            "😂", "🤣", "😭", "❤️", "🔥", "👏",
            "💀", "😍", "🥺", "😱",
        ],
        "negative": [
            "Sadge", "BibleThump", "NotLikeThis",
            "PepeHands", "Pepega", "KEKL",
        ],
    },
}

# Flatten all keywords into a single lookup set (lowercased) for fast scanning
_ALL_KEYWORDS_LOWER: set[str] = set()
_KEYWORD_CATEGORY: dict[str, str] = {}  # keyword -> category (excitement/emotion/etc.)

for _lang, _categories in KEYWORDS.items():
    for _category, _words in _categories.items():
        for _word in _words:
            _lower = _word.lower()
            _ALL_KEYWORDS_LOWER.add(_lower)
            _KEYWORD_CATEGORY[_lower] = _category

# Spam patterns to IGNORE in chat
SPAM_PATTERNS = [
    r"^7{3,}$",        # 7777777
    r"^![\w]+",        # !command
    r"^/[\w]+",        # /command
    r"^https?://",     # URLs
]
_SPAM_REGEXES = [re.compile(p, re.IGNORECASE) for p in SPAM_PATTERNS]


# ══════════════════════════════════════════════════════════════════
#  HELPER: z-score normalization
# ══════════════════════════════════════════════════════════════════

def z_score_normalize(values: np.ndarray) -> np.ndarray:
    """
    Z-score normalize an array. Returns 0 for constant arrays.
    Output is clipped to [0, 1] range for scoring.
    """
    if len(values) == 0:
        return values
    std = np.std(values)
    if std < 1e-10:
        return np.zeros_like(values)
    z = (values - np.mean(values)) / std
    # Clip to [0, 1]: only positive z-scores matter (above-average moments)
    return np.clip(z / 3.0 + 0.5, 0.0, 1.0)


def normalize_0_1(values: np.ndarray) -> np.ndarray:
    """Min-max normalize to [0, 1] range."""
    if len(values) == 0:
        return values
    vmin, vmax = np.min(values), np.max(values)
    if vmax - vmin < 1e-10:
        return np.zeros_like(values)
    return (values - vmin) / (vmax - vmin)


# ══════════════════════════════════════════════════════════════════
#  SIGNAL 1: Chat spike detection
# ══════════════════════════════════════════════════════════════════

def _is_spam(message: str) -> bool:
    """Check if a chat message is spam."""
    for regex in _SPAM_REGEXES:
        if regex.match(message.strip()):
            return True
    return False


def compute_chat_signal(
    chat_messages: list[ChatMessage],
    duration: float,
    window_size: int = 60,
    step_size: int = 10,
) -> np.ndarray:
    """
    Compute chat spike signal using sliding window.

    Counts unique authors per window (not raw message count)
    to reduce spam bias. Super chats get 3x weight.

    Returns:
        Array of chat rate values, one per window step.
    """
    if not chat_messages or duration <= 0:
        n_steps = max(1, int(duration / step_size)) if duration > 0 else 1
        return np.zeros(n_steps)

    # Filter spam
    valid_messages = [m for m in chat_messages if not _is_spam(m.message)]

    n_steps = max(1, int((duration - window_size) / step_size) + 1)
    rates = np.zeros(n_steps)

    for i in range(n_steps):
        window_start = i * step_size
        window_end = window_start + window_size

        # Count unique authors in this window (reduces spam impact)
        authors_in_window: dict[str, float] = {}
        for msg in valid_messages:
            if window_start <= msg.timestamp < window_end:
                weight = 3.0 if msg.is_superchat else (1.5 if msg.is_member else 1.0)
                author = msg.author
                if author not in authors_in_window or authors_in_window[author] < weight:
                    authors_in_window[author] = weight

        rates[i] = sum(authors_in_window.values())

    return rates


# ══════════════════════════════════════════════════════════════════
#  SIGNAL 2: Audio energy peaks
# ══════════════════════════════════════════════════════════════════

def compute_audio_signal(
    audio_path: Path,
    duration: float,
    window_size: int = 60,
    step_size: int = 10,
) -> np.ndarray:
    """
    Compute audio energy signal using librosa RMS analysis.

    Calculates RMS energy in sliding windows to detect moments
    of high audio intensity (shouting, laughter, excitement).

    Returns:
        Array of energy values, one per window step.
    """
    import librosa

    n_steps = max(1, int((duration - window_size) / step_size) + 1)

    try:
        # Load audio (librosa handles resampling)
        y, sr = librosa.load(str(audio_path), sr=16000, mono=True)
    except Exception as e:
        logger.error(f"Failed to load audio for energy analysis: {e}")
        return np.zeros(n_steps)

    # Compute RMS energy with fine granularity
    hop_length = 512
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    rms_times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)

    # Aggregate into sliding windows
    energies = np.zeros(n_steps)
    for i in range(n_steps):
        window_start = i * step_size
        window_end = window_start + window_size

        mask = (rms_times >= window_start) & (rms_times < window_end)
        if np.any(mask):
            # Use 90th percentile instead of mean to capture peaks
            energies[i] = np.percentile(rms[mask], 90)

    return energies


# ══════════════════════════════════════════════════════════════════
#  SIGNAL 3: Keyword triggers
# ══════════════════════════════════════════════════════════════════

@dataclass
class KeywordHit:
    """A keyword match in the transcript."""
    time: float
    keyword: str
    category: str
    source: str  # "transcript" or "chat"


def scan_keywords_in_transcript(
    transcript: list[TranscriptSegment],
    window_size: int = 60,
    step_size: int = 10,
    duration: float = 0.0,
) -> tuple[np.ndarray, list[KeywordHit]]:
    """
    Scan transcript segments for VTuber-specific keywords.

    Returns:
        Tuple of (keyword_scores_per_window, list_of_keyword_hits)
    """
    if not duration and transcript:
        duration = max(s.end for s in transcript)

    n_steps = max(1, int((duration - window_size) / step_size) + 1)
    scores = np.zeros(n_steps)
    hits: list[KeywordHit] = []

    for seg in transcript:
        text_lower = seg.text.lower()

        for kw in _ALL_KEYWORDS_LOWER:
            if kw in text_lower:
                category = _KEYWORD_CATEGORY.get(kw, "unknown")
                mid_time = (seg.start + seg.end) / 2.0

                hits.append(KeywordHit(
                    time=mid_time,
                    keyword=kw,
                    category=category,
                    source="transcript",
                ))

                # Add to the corresponding window
                step_idx = int(mid_time / step_size)
                if 0 <= step_idx < n_steps:
                    # Weight by category importance
                    weight = {
                        "excitement": 1.5,
                        "surprise": 1.3,
                        "action": 1.2,
                        "emotion": 1.0,
                        "positive": 1.0,
                        "negative": 0.5,
                    }.get(category, 1.0)
                    scores[step_idx] += weight

    return scores, hits


def scan_keywords_in_chat(
    chat_messages: list[ChatMessage],
    window_size: int = 60,
    step_size: int = 10,
    duration: float = 0.0,
) -> tuple[np.ndarray, list[KeywordHit]]:
    """
    Scan chat messages for VTuber-specific keywords.
    """
    if not duration and chat_messages:
        duration = max(m.timestamp for m in chat_messages)

    n_steps = max(1, int((duration - window_size) / step_size) + 1)
    scores = np.zeros(n_steps)
    hits: list[KeywordHit] = []

    for msg in chat_messages:
        if _is_spam(msg.message):
            continue

        text_lower = msg.message.lower()

        for kw in _ALL_KEYWORDS_LOWER:
            if kw in text_lower:
                category = _KEYWORD_CATEGORY.get(kw, "unknown")

                hits.append(KeywordHit(
                    time=msg.timestamp,
                    keyword=kw,
                    category=category,
                    source="chat",
                ))

                step_idx = int(msg.timestamp / step_size)
                if 0 <= step_idx < n_steps:
                    weight = 1.0
                    if msg.is_superchat:
                        weight = 2.0
                    scores[step_idx] += weight

    return scores, hits


# ══════════════════════════════════════════════════════════════════
#  HIGHLIGHT DETECTION — main algorithm
# ══════════════════════════════════════════════════════════════════

def detect_highlights(
    transcript: list[TranscriptSegment],
    chat_messages: list[ChatMessage],
    audio_path: Optional[Path],
    duration: float,
    window_size: int | None = None,
    step_size: int | None = None,
    min_score: float | None = None,
    max_gap: int | None = None,
    weight_chat: float | None = None,
    weight_audio: float | None = None,
    weight_keyword: float | None = None,
) -> list[Highlight]:
    """
    Multi-signal highlight detection for VTuber streams.

    Algorithm:
      1. Compute chat spike signal (sliding window, z-score)
      2. Compute audio energy signal (librosa RMS, z-score)
      3. Compute keyword trigger signal (transcript + chat scan)
      4. Weighted fusion → composite score per window
      5. Peak finding above threshold
      6. Merge overlapping/nearby highlights
      7. Snap boundaries to sentence edges
      8. Classify highlight type
      9. Return sorted by score (descending)

    Args:
        transcript: Whisper-generated transcript segments
        chat_messages: Parsed live chat messages
        audio_path: Path to audio file (WAV) for energy analysis
        duration: Total video duration in seconds
        All other params override settings defaults.

    Returns:
        List of Highlight objects, sorted by score descending.
    """
    # Use defaults from config
    ws = window_size or settings.highlight_window_size
    ss = step_size or settings.highlight_step_size
    ms = min_score if min_score is not None else settings.highlight_min_score
    mg = max_gap or settings.highlight_max_gap
    wc = weight_chat or settings.weight_chat
    wa = weight_audio or settings.weight_audio
    wk = weight_keyword or settings.weight_keyword

    logger.info(
        f"Detecting highlights: duration={duration:.0f}s, "
        f"window={ws}s, step={ss}s, min_score={ms}, "
        f"weights=(chat={wc}, audio={wa}, keyword={wk})"
    )

    n_steps = max(1, int((duration - ws) / ss) + 1)

    # ── Signal 1: Chat spikes ────────────────────────────────
    chat_raw = compute_chat_signal(chat_messages, duration, ws, ss)
    # Ensure same length
    chat_raw = _pad_or_trim(chat_raw, n_steps)
    chat_scores = z_score_normalize(chat_raw)
    logger.info(f"Chat signal: mean={np.mean(chat_raw):.2f}, max={np.max(chat_raw):.2f}, {len(chat_messages)} messages")

    # ── Signal 2: Audio energy ───────────────────────────────
    if audio_path and audio_path.exists():
        audio_raw = compute_audio_signal(audio_path, duration, ws, ss)
        audio_raw = _pad_or_trim(audio_raw, n_steps)
        audio_scores = z_score_normalize(audio_raw)
        logger.info(f"Audio signal: mean={np.mean(audio_raw):.4f}, max={np.max(audio_raw):.4f}")
    else:
        audio_scores = np.full(n_steps, 0.5)  # neutral if no audio
        logger.warning("No audio path — using neutral audio signal")

    # ── Signal 3: Keyword triggers ───────────────────────────
    kw_transcript_scores, kw_transcript_hits = scan_keywords_in_transcript(
        transcript, ws, ss, duration
    )
    kw_chat_scores, kw_chat_hits = scan_keywords_in_chat(
        chat_messages, ws, ss, duration
    )
    # Combine keyword signals from both sources
    kw_combined = _pad_or_trim(kw_transcript_scores, n_steps) + _pad_or_trim(kw_chat_scores, n_steps)
    keyword_scores = normalize_0_1(kw_combined)

    all_kw_hits = kw_transcript_hits + kw_chat_hits
    logger.info(f"Keyword signal: {len(all_kw_hits)} hits ({len(kw_transcript_hits)} transcript, {len(kw_chat_hits)} chat)")

    # ── Composite scoring ────────────────────────────────────
    composite = (
        wc * chat_scores
        + wa * audio_scores
        + wk * keyword_scores
    )

    logger.info(
        f"Composite scores: mean={np.mean(composite):.3f}, "
        f"max={np.max(composite):.3f}, "
        f"above threshold ({ms}): {np.sum(composite >= ms)} windows"
    )

    # ── Find peaks ───────────────────────────────────────────
    # Use scipy to find local maxima above threshold
    peak_indices, peak_properties = scipy_find_peaks(
        composite,
        height=ms,
        distance=max(1, int(30 / ss)),  # at least 30s apart
        prominence=0.05,
    )

    if len(peak_indices) == 0:
        # Fallback: if no peaks found, take the top N windows above a lower threshold
        fallback_threshold = ms * 0.75
        above_threshold = np.where(composite >= fallback_threshold)[0]
        if len(above_threshold) > 0:
            # Take top 5
            sorted_idx = above_threshold[np.argsort(composite[above_threshold])[::-1]]
            peak_indices = sorted_idx[:5]
            logger.info(f"No scipy peaks found; fallback selected {len(peak_indices)} windows")
        else:
            logger.info("No highlights found above threshold")
            return []

    logger.info(f"Found {len(peak_indices)} peak windows")

    # ── Build raw highlights ─────────────────────────────────
    raw_highlights: list[dict] = []
    for idx in peak_indices:
        t_start = idx * ss
        t_end = t_start + ws
        score = float(composite[idx])

        # Determine contributing signals
        signals = []
        if chat_scores[idx] > 0.6:
            signals.append("chat")
        if audio_scores[idx] > 0.6:
            signals.append("audio")
        if keyword_scores[idx] > 0.3:
            signals.append("keyword")

        raw_highlights.append({
            "start": t_start,
            "end": min(t_end, duration),
            "score": score,
            "chat_intensity": float(chat_scores[idx]),
            "audio_energy": float(audio_scores[idx]),
            "keyword_score": float(keyword_scores[idx]),
            "signals": signals,
        })

    # ── Merge overlapping highlights ─────────────────────────
    merged = _merge_overlapping(raw_highlights, mg)
    logger.info(f"After merging: {len(merged)} highlights")

    # ── Snap to sentence boundaries ──────────────────────────
    for h in merged:
        h["start"], h["end"] = _snap_to_sentences(
            h["start"], h["end"], transcript
        )

    # ── Enforce duration limits ──────────────────────────────
    for h in merged:
        clip_dur = h["end"] - h["start"]
        if clip_dur > settings.clip_max_duration:
            # Center the window on the peak
            center = (h["start"] + h["end"]) / 2
            h["start"] = max(0, center - settings.clip_max_duration / 2)
            h["end"] = min(duration, center + settings.clip_max_duration / 2)
        elif clip_dur < settings.clip_min_duration:
            # Expand symmetrically
            deficit = settings.clip_min_duration - clip_dur
            h["start"] = max(0, h["start"] - deficit / 2)
            h["end"] = min(duration, h["end"] + deficit / 2)

    # ── Build Highlight objects ──────────────────────────────
    highlights: list[Highlight] = []
    for h in merged:
        # Extract transcript snippet
        snippet = _get_transcript_snippet(transcript, h["start"], h["end"])

        # Classify highlight type
        hl_type = _classify_highlight(h, all_kw_hits)

        # Generate description
        desc = _generate_description(h, hl_type, snippet)

        highlights.append(
            Highlight(
                start_time=round(h["start"], 2),
                end_time=round(h["end"], 2),
                score=round(h["score"], 4),
                highlight_type=hl_type,
                description=desc,
                transcript_snippet=snippet[:300],
                chat_intensity=round(h["chat_intensity"], 4),
                audio_energy=round(h["audio_energy"], 4),
                keyword_score=round(h["keyword_score"], 4),
                contributing_signals=h["signals"],
            )
        )

    # Sort by score descending
    highlights.sort(key=lambda x: x.score, reverse=True)

    logger.info(f"Final highlights: {len(highlights)}")
    for i, h in enumerate(highlights[:5]):
        logger.info(
            f"  #{i+1}: [{h.start_time:.0f}s–{h.end_time:.0f}s] "
            f"score={h.score:.3f} type={h.highlight_type.value} "
            f"signals={h.contributing_signals}"
        )

    return highlights


# ══════════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════

def _pad_or_trim(arr: np.ndarray, target_len: int) -> np.ndarray:
    """Pad or trim array to target length."""
    if len(arr) >= target_len:
        return arr[:target_len]
    return np.pad(arr, (0, target_len - len(arr)), mode="constant")


def _merge_overlapping(highlights: list[dict], max_gap: int) -> list[dict]:
    """
    Merge highlights that overlap or are within max_gap seconds of each other.
    """
    if not highlights:
        return []

    sorted_hl = sorted(highlights, key=lambda h: h["start"])
    merged: list[dict] = [sorted_hl[0].copy()]

    for h in sorted_hl[1:]:
        last = merged[-1]
        if h["start"] <= last["end"] + max_gap:
            # Merge: extend the end, take the higher score
            last["end"] = max(last["end"], h["end"])
            last["score"] = max(last["score"], h["score"])
            last["chat_intensity"] = max(last["chat_intensity"], h["chat_intensity"])
            last["audio_energy"] = max(last["audio_energy"], h["audio_energy"])
            last["keyword_score"] = max(last["keyword_score"], h["keyword_score"])
            # Combine signals
            last["signals"] = list(set(last["signals"]) | set(h["signals"]))
        else:
            merged.append(h.copy())

    return merged


def _snap_to_sentences(
    start: float,
    end: float,
    transcript: list[TranscriptSegment],
) -> tuple[float, float]:
    """
    Snap highlight boundaries to the nearest sentence boundaries
    from the transcript, avoiding cutting mid-sentence.
    """
    if not transcript:
        return start, end

    # Find the transcript segment that contains or is nearest to the start
    best_start = start
    best_end = end

    for seg in transcript:
        # Snap start: find the nearest segment start that's ≤ our start
        if seg.start <= start <= seg.end:
            best_start = seg.start
        elif seg.end < start and abs(seg.end - start) < 3.0:
            best_start = seg.end

        # Snap end: find the nearest segment end that's ≥ our end
        if seg.start <= end <= seg.end:
            best_end = seg.end
        elif seg.start > end and abs(seg.start - end) < 3.0:
            best_end = seg.start

    return best_start, best_end


def _get_transcript_snippet(
    transcript: list[TranscriptSegment],
    start: float,
    end: float,
) -> str:
    """Extract transcript text within a time range."""
    texts = []
    for seg in transcript:
        if seg.end >= start and seg.start <= end:
            texts.append(seg.text)
    return " ".join(texts)


def _classify_highlight(
    highlight: dict,
    keyword_hits: list[KeywordHit],
) -> HighlightType:
    """
    Classify a highlight's type based on the dominant keyword categories
    and signal pattern.
    """
    # Find keyword hits in this highlight's time range
    relevant_hits = [
        h for h in keyword_hits
        if highlight["start"] <= h.time <= highlight["end"]
    ]

    if not relevant_hits:
        # Classify by signal pattern
        if highlight["chat_intensity"] > 0.8:
            return HighlightType.EXCITING
        if highlight["audio_energy"] > 0.8:
            return HighlightType.FUNNY
        return HighlightType.MIXED

    # Count categories
    category_counts: dict[str, int] = {}
    for hit in relevant_hits:
        category_counts[hit.category] = category_counts.get(hit.category, 0) + 1

    dominant = max(category_counts, key=category_counts.get)  # type: ignore

    category_to_type = {
        "excitement": HighlightType.EXCITING,
        "surprise": HighlightType.EXCITING,
        "emotion": HighlightType.EMOTIONAL,
        "action": HighlightType.SKILL,
        "positive": HighlightType.FUNNY,
        "negative": HighlightType.EMOTIONAL,
    }

    return category_to_type.get(dominant, HighlightType.MIXED)


def _generate_description(
    highlight: dict,
    hl_type: HighlightType,
    snippet: str,
) -> str:
    """Generate a human-readable description for a highlight."""
    type_labels = {
        HighlightType.FUNNY: "Funny moment",
        HighlightType.EXCITING: "Exciting moment",
        HighlightType.EMOTIONAL: "Emotional moment",
        HighlightType.SKILL: "Impressive gameplay/action",
        HighlightType.MIXED: "Notable moment",
    }
    label = type_labels.get(hl_type, "Highlight")

    signals_desc = []
    if "chat" in highlight["signals"]:
        signals_desc.append("high chat activity")
    if "audio" in highlight["signals"]:
        signals_desc.append("audio spike")
    if "keyword" in highlight["signals"]:
        signals_desc.append("reaction keywords detected")

    desc = f"{label}"
    if signals_desc:
        desc += f" ({', '.join(signals_desc)})"

    # Add time info
    start_min = int(highlight["start"] // 60)
    start_sec = int(highlight["start"] % 60)
    desc += f" at {start_min}:{start_sec:02d}"

    return desc
