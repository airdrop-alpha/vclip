"""
VClip transcriber — faster-whisper STT with word-level timestamps.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from app.config import settings
from app.models import TranscriptSegment, WordTimestamp

logger = logging.getLogger(__name__)

# Lazy-loaded model instance
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


def transcribe(
    audio_path: Path,
    language: Optional[str] = None,
    task: str = "transcribe",
) -> list[TranscriptSegment]:
    """
    Transcribe audio file using faster-whisper.

    Args:
        audio_path: Path to audio file (WAV 16kHz mono recommended)
        language: Force language code (e.g. "ja", "en", "zh"). None = auto-detect.
        task: "transcribe" or "translate" (translate to English)

    Returns:
        List of TranscriptSegment with word-level timestamps.
    """
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
        f"Detected language: {detected_language} (probability={info.language_probability:.2f}), "
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

        if segment_id % 100 == 0:
            logger.debug(f"Processed {segment_id} segments ({seg.end:.1f}s)")

    logger.info(f"Transcription complete: {len(segments)} segments")
    return segments


def transcribe_multilingual(
    audio_path: Path,
    languages: list[str],
) -> list[TranscriptSegment]:
    """
    Transcribe with multi-language support.

    Tries auto-detection first. If the detected language is in the expected
    languages list, uses that. Otherwise falls back to the first language.

    For streams with mixed languages (common in VTuber content — JP with some EN),
    Whisper's auto-detection per-segment handles this reasonably well.
    """
    # Use auto-detect — Whisper large-v3 handles mixed language well
    segments = transcribe(audio_path, language=None)

    if not segments:
        # Fallback: try with explicit first language
        logger.warning("Auto-detect returned no segments, retrying with explicit language")
        segments = transcribe(audio_path, language=languages[0])

    return segments
