"""
VClip transcriber — multi-backend STT with word-level timestamps.

Backends:
  - api (default): OpenAI-compatible Whisper API (Groq / OpenAI)
  - local: faster-whisper local model (fallback)
"""
from __future__ import annotations

import json
import logging
import math
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import httpx

from app.config import settings
from app.models import TranscriptSegment, WordTimestamp

logger = logging.getLogger(__name__)

# ── Local model (lazy) ────────────────────────────────────────
_model = None


def _get_model():
    """Lazy-load the faster-whisper model (expensive to initialize)."""
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        logger.info(
            f"Loading Whisper model: {settings.whisper_model} "
            f"(device={settings.whisper_device}, compute={settings.whisper_compute_type})"
        )
        _model = WhisperModel(
            settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
        logger.info("Whisper model loaded successfully")
    return _model


# ── Audio chunking ────────────────────────────────────────────

def _get_audio_duration(path: Path) -> float:
    """Get audio duration in seconds using ffprobe."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet", "-show_entries",
            "format=duration", "-of", "csv=p=0", str(path),
        ],
        capture_output=True, text=True,
    )
    return float(result.stdout.strip())


def _split_audio(audio_path: Path, chunk_seconds: int = 600) -> list[Path]:
    """
    Split audio into chunks of chunk_seconds (default 10 min).
    Returns list of chunk file paths.
    Each chunk is converted to mp3 to stay under 25MB API limit.
    """
    duration = _get_audio_duration(audio_path)
    if duration <= chunk_seconds:
        # Single chunk — just convert to mp3 if needed
        if audio_path.suffix == ".mp3" and audio_path.stat().st_size < 24 * 1024 * 1024:
            return [audio_path]
        tmp = Path(tempfile.mktemp(suffix=".mp3", dir=settings.temp_dir))
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(audio_path),
                "-ac", "1", "-ar", "16000", "-b:a", "64k",
                str(tmp),
            ],
            capture_output=True, check=True,
        )
        return [tmp]

    num_chunks = math.ceil(duration / chunk_seconds)
    chunks: list[Path] = []

    for i in range(num_chunks):
        start = i * chunk_seconds
        tmp = Path(tempfile.mktemp(suffix=f"_chunk{i:03d}.mp3", dir=settings.temp_dir))
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(audio_path),
                "-ss", str(start), "-t", str(chunk_seconds),
                "-ac", "1", "-ar", "16000", "-b:a", "64k",
                str(tmp),
            ],
            capture_output=True, check=True,
        )
        chunks.append(tmp)

    logger.info(f"Split audio into {len(chunks)} chunks ({chunk_seconds}s each)")
    return chunks


# ── API backend ───────────────────────────────────────────────

def _transcribe_chunk_api(
    audio_path: Path,
    language: Optional[str] = None,
    offset: float = 0.0,
) -> tuple[list[TranscriptSegment], str]:
    """
    Transcribe a single audio chunk via OpenAI-compatible API.
    Returns (segments, detected_language).
    """
    api_url = settings.whisper_api_url
    api_key = settings.whisper_api_key
    model = settings.whisper_api_model

    if not api_key:
        raise RuntimeError("VCLIP_WHISPER_API_KEY not set — cannot use API backend")

    headers = {"Authorization": f"Bearer {api_key}"}

    data = {
        "model": model,
        "response_format": "verbose_json",
        "timestamp_granularities[]": "word",
    }
    if language:
        data["language"] = language

    with open(audio_path, "rb") as f:
        files = {"file": (audio_path.name, f, "audio/mpeg")}

        with httpx.Client(timeout=300.0) as client:
            resp = client.post(api_url, headers=headers, data=data, files=files)

    if resp.status_code != 200:
        logger.error(f"Whisper API error {resp.status_code}: {resp.text[:500]}")
        resp.raise_for_status()

    result = resp.json()
    detected_lang = result.get("language", language or "unknown")

    segments: list[TranscriptSegment] = []
    seg_id = 0

    # Parse segments from response
    api_segments = result.get("segments", [])
    api_words = result.get("words", [])

    if api_segments:
        for seg in api_segments:
            seg_start = seg.get("start", 0.0) + offset
            seg_end = seg.get("end", 0.0) + offset
            text = seg.get("text", "").strip()
            if not text:
                continue

            # Find words that belong to this segment's time range
            seg_words: list[WordTimestamp] = []
            for w in api_words:
                w_start = w.get("start", 0.0)
                w_end = w.get("end", 0.0)
                if w_start >= seg.get("start", 0.0) - 0.1 and w_end <= seg.get("end", 0.0) + 0.1:
                    seg_words.append(
                        WordTimestamp(
                            word=w.get("word", ""),
                            start=w_start + offset,
                            end=w_end + offset,
                            probability=1.0,  # API doesn't always provide this
                        )
                    )

            segments.append(
                TranscriptSegment(
                    id=seg_id,
                    start=seg_start,
                    end=seg_end,
                    text=text,
                    language=detected_lang,
                    words=seg_words,
                )
            )
            seg_id += 1
    elif result.get("text"):
        # Fallback: no segments, just full text with words
        all_words: list[WordTimestamp] = []
        for w in api_words:
            all_words.append(
                WordTimestamp(
                    word=w.get("word", ""),
                    start=w.get("start", 0.0) + offset,
                    end=w.get("end", 0.0) + offset,
                    probability=1.0,
                )
            )

        segments.append(
            TranscriptSegment(
                id=0,
                start=offset,
                end=(api_words[-1]["end"] + offset) if api_words else offset,
                text=result["text"].strip(),
                language=detected_lang,
                words=all_words,
            )
        )

    return segments, detected_lang


def _transcribe_api(
    audio_path: Path,
    language: Optional[str] = None,
) -> list[TranscriptSegment]:
    """Transcribe audio file via API, handling chunking for large files."""
    chunks = _split_audio(audio_path)
    all_segments: list[TranscriptSegment] = []
    chunk_seconds = 600  # must match _split_audio default

    try:
        for i, chunk_path in enumerate(chunks):
            offset = i * chunk_seconds if len(chunks) > 1 else 0.0
            logger.info(
                f"Transcribing chunk {i + 1}/{len(chunks)} "
                f"(offset={offset:.0f}s, file={chunk_path.name})"
            )

            segs, lang = _transcribe_chunk_api(chunk_path, language=language, offset=offset)
            all_segments.extend(segs)
            logger.info(f"Chunk {i + 1}: {len(segs)} segments, language={lang}")

    finally:
        # Clean up temp chunk files
        for chunk_path in chunks:
            if chunk_path != audio_path:
                try:
                    chunk_path.unlink()
                except OSError:
                    pass

    # Re-number segment IDs
    for idx, seg in enumerate(all_segments):
        seg.id = idx

    logger.info(f"API transcription complete: {len(all_segments)} segments total")
    return all_segments


# ── Local backend ─────────────────────────────────────────────

def _transcribe_local(
    audio_path: Path,
    language: Optional[str] = None,
    task: str = "transcribe",
) -> list[TranscriptSegment]:
    """Transcribe using local faster-whisper model."""
    model = _get_model()

    logger.info(f"Transcribing {audio_path} (language={language or 'auto'}, task={task})")

    segments_gen, info = model.transcribe(
        str(audio_path),
        language=language,
        task=task,
        beam_size=5,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters=dict(
            min_silence_duration_ms=500,
            speech_pad_ms=200,
        ),
    )

    detected_language = info.language
    logger.info(
        f"Detected language: {detected_language} "
        f"(probability={info.language_probability:.2f}), "
        f"duration={info.duration:.1f}s"
    )

    segments: list[TranscriptSegment] = []
    segment_id = 0

    for seg in segments_gen:
        words: list[WordTimestamp] = []
        if seg.words:
            for w in seg.words:
                words.append(
                    WordTimestamp(
                        word=w.word,
                        start=w.start,
                        end=w.end,
                        probability=w.probability,
                    )
                )

        segments.append(
            TranscriptSegment(
                id=segment_id,
                start=seg.start,
                end=seg.end,
                text=seg.text.strip(),
                language=detected_language,
                words=words,
            )
        )
        segment_id += 1

    logger.info(f"Transcription complete: {len(segments)} segments")
    return segments



# ── Replicate backend ─────────────────────────────────────────

def _upload_file_data_url(audio_path: Path) -> str:
    """Convert audio file to a data URL for Replicate API."""
    import base64
    with open(audio_path, 'rb') as f:
        data = base64.b64encode(f.read()).decode()
    suffix = audio_path.suffix.lstrip('.')
    mime = {'mp3': 'audio/mpeg', 'wav': 'audio/wav', 'mp4': 'audio/mp4',
            'ogg': 'audio/ogg', 'm4a': 'audio/mp4'}.get(suffix, 'audio/mpeg')
    return f'data:{mime};base64,{data}'


def _transcribe_chunk_replicate(
    audio_path: Path,
    language: Optional[str] = None,
    offset: float = 0.0,
) -> tuple[list[TranscriptSegment], str]:
    """
    Transcribe a single audio chunk via Replicate API.
    Returns (segments, detected_language).
    """
    api_token = settings.replicate_api_token
    model = settings.replicate_whisper_model

    if not api_token:
        raise RuntimeError("REPLICATE_API_TOKEN not set — cannot use Replicate backend")

    # Use Replicate HTTP API directly (no SDK dependency)
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
        "Prefer": "wait",  # synchronous mode
    }

    audio_data_url = _upload_file_data_url(audio_path)

    payload = {
        "input": {
            "audio": audio_data_url,
            "word_timestamps": True,
        }
    }
    if language:
        payload["input"]["language"] = language

    api_url = f"https://api.replicate.com/v1/models/{model}/predictions"

    with httpx.Client(timeout=600.0) as client:
        resp = client.post(api_url, headers=headers, json=payload)

    if resp.status_code not in (200, 201):
        logger.error(f"Replicate API error {resp.status_code}: {resp.text[:500]}")
        resp.raise_for_status()

    result = resp.json()

    # If prediction is still processing, poll for completion
    if result.get("status") in ("starting", "processing"):
        poll_url = result.get("urls", {}).get("get", "")
        if poll_url:
            import time
            for _ in range(120):  # max 10 min
                time.sleep(5)
                poll_resp = client.get(poll_url, headers={"Authorization": f"Bearer {api_token}"})
                result = poll_resp.json()
                if result.get("status") in ("succeeded", "failed", "canceled"):
                    break

    if result.get("status") == "failed":
        error = result.get("error", "Unknown error")
        raise RuntimeError(f"Replicate prediction failed: {error}")

    output = result.get("output", result)

    # Parse Replicate whisper output format
    detected_lang = output.get("detected_language", language or "unknown")
    segments: list[TranscriptSegment] = []

    api_segments = output.get("segments", [])

    for seg_id, seg in enumerate(api_segments):
        seg_start = seg.get("start", 0.0) + offset
        seg_end = seg.get("end", 0.0) + offset
        text = seg.get("text", "").strip()
        if not text:
            continue

        # Parse word-level timestamps
        seg_words: list[WordTimestamp] = []
        for w in seg.get("words", []):
            seg_words.append(
                WordTimestamp(
                    word=w.get("word", ""),
                    start=w.get("start", 0.0) + offset,
                    end=w.get("end", 0.0) + offset,
                    probability=w.get("probability", 1.0),
                )
            )

        segments.append(
            TranscriptSegment(
                id=seg_id,
                start=seg_start,
                end=seg_end,
                text=text,
                language=detected_lang,
                words=seg_words,
            )
        )

    if not segments and output.get("transcription"):
        # Fallback: just text, no segments
        segments.append(
            TranscriptSegment(
                id=0,
                start=offset,
                end=offset,
                text=output["transcription"].strip(),
                language=detected_lang,
                words=[],
            )
        )

    return segments, detected_lang


def _transcribe_replicate(
    audio_path: Path,
    language: Optional[str] = None,
) -> list[TranscriptSegment]:
    """Transcribe audio file via Replicate, handling chunking for large files."""
    chunks = _split_audio(audio_path)
    all_segments: list[TranscriptSegment] = []
    chunk_seconds = 600

    try:
        for i, chunk_path in enumerate(chunks):
            offset = i * chunk_seconds if len(chunks) > 1 else 0.0
            logger.info(
                f"Transcribing chunk {i + 1}/{len(chunks)} via Replicate "
                f"(offset={offset:.0f}s, file={chunk_path.name})"
            )

            segs, lang = _transcribe_chunk_replicate(chunk_path, language=language, offset=offset)
            all_segments.extend(segs)
            logger.info(f"Chunk {i + 1}: {len(segs)} segments, language={lang}")

    finally:
        for chunk_path in chunks:
            if chunk_path != audio_path:
                try:
                    chunk_path.unlink()
                except OSError:
                    pass

    for idx, seg in enumerate(all_segments):
        seg.id = idx

    logger.info(f"Replicate transcription complete: {len(all_segments)} segments total")
    return all_segments

# ── Public interface ──────────────────────────────────────────

def transcribe(
    audio_path: Path,
    language: Optional[str] = None,
    task: str = "transcribe",
) -> list[TranscriptSegment]:
    """
    Transcribe audio file using configured backend.

    Backend selection:
      - VCLIP_WHISPER_BACKEND=api  → OpenAI/Groq API (default)
      - VCLIP_WHISPER_BACKEND=local → faster-whisper local model
    """
    backend = settings.whisper_backend

    if backend == "replicate":
        try:
            return _transcribe_replicate(audio_path, language=language)
        except Exception as e:
            logger.error(f"Replicate transcription failed: {e}")
            # Try API fallback
            if settings.whisper_api_key:
                logger.warning("Falling back to OpenAI API...")
                try:
                    return _transcribe_api(audio_path, language=language)
                except Exception:
                    pass
            # Try local fallback
            try:
                logger.warning("Falling back to local whisper model...")
                return _transcribe_local(audio_path, language=language, task=task)
            except ImportError:
                logger.error("All transcription backends failed")
                raise e
    elif backend == "api":
        try:
            return _transcribe_api(audio_path, language=language)
        except Exception as e:
            logger.error(f"API transcription failed: {e}")
            try:
                logger.warning("Falling back to local whisper model...")
                return _transcribe_local(audio_path, language=language, task=task)
            except ImportError:
                logger.error("Local fallback unavailable (faster-whisper not installed)")
                raise e
    else:
        return _transcribe_local(audio_path, language=language, task=task)


def transcribe_multilingual(
    audio_path: Path,
    languages: list[str],
) -> list[TranscriptSegment]:
    """
    Transcribe with multi-language support.

    Tries auto-detection first. If no results, retries with explicit language.
    """
    segments = transcribe(audio_path, language=None)

    if not segments and languages:
        logger.warning("Auto-detect returned no segments, retrying with explicit language")
        segments = transcribe(audio_path, language=languages[0])

    return segments
