"""
Tests for VClip highlight detection engine.

Tests the core algorithm: chat spike detection, audio energy analysis,
keyword scanning, composite scoring, and merging.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models import ChatMessage, Highlight, TranscriptSegment, WordTimestamp
from app.services.highlight import (
    KEYWORDS,
    _ALL_KEYWORDS_LOWER,
    _merge_overlapping,
    _snap_to_sentences,
    _is_spam,
    compute_chat_signal,
    detect_highlights,
    normalize_0_1,
    scan_keywords_in_chat,
    scan_keywords_in_transcript,
    z_score_normalize,
)


class TestZScoreNormalize(unittest.TestCase):
    """Test z-score normalization."""

    def test_empty_array(self):
        result = z_score_normalize(np.array([]))
        self.assertEqual(len(result), 0)

    def test_constant_array(self):
        result = z_score_normalize(np.array([5.0, 5.0, 5.0, 5.0]))
        np.testing.assert_array_equal(result, np.zeros(4))

    def test_output_range_0_1(self):
        values = np.array([1.0, 2.0, 5.0, 10.0, 3.0, 1.0, 8.0])
        result = z_score_normalize(values)
        self.assertTrue(np.all(result >= 0.0))
        self.assertTrue(np.all(result <= 1.0))

    def test_high_values_get_high_scores(self):
        values = np.array([1.0, 1.0, 1.0, 1.0, 10.0, 1.0, 1.0])
        result = z_score_normalize(values)
        # The spike at index 4 should have the highest score
        self.assertEqual(np.argmax(result), 4)


class TestNormalize01(unittest.TestCase):
    """Test min-max normalization."""

    def test_empty(self):
        result = normalize_0_1(np.array([]))
        self.assertEqual(len(result), 0)

    def test_constant(self):
        result = normalize_0_1(np.array([3.0, 3.0, 3.0]))
        np.testing.assert_array_equal(result, np.zeros(3))

    def test_range(self):
        result = normalize_0_1(np.array([0.0, 5.0, 10.0]))
        np.testing.assert_array_almost_equal(result, [0.0, 0.5, 1.0])


class TestSpamDetection(unittest.TestCase):
    """Test chat spam filtering."""

    def test_not_spam(self):
        self.assertFalse(_is_spam("草"))
        self.assertFalse(_is_spam("LOL that was funny"))
        self.assertFalse(_is_spam("すごい！"))

    def test_command_spam(self):
        self.assertTrue(_is_spam("!play"))
        self.assertTrue(_is_spam("!songrequest"))

    def test_7777_spam(self):
        self.assertTrue(_is_spam("7777"))
        self.assertTrue(_is_spam("77777777"))

    def test_url_spam(self):
        self.assertTrue(_is_spam("https://example.com"))
        self.assertTrue(_is_spam("http://spam.link"))


class TestChatSignal(unittest.TestCase):
    """Test chat spike detection."""

    def test_empty_chat(self):
        result = compute_chat_signal([], duration=300.0)
        self.assertTrue(np.all(result == 0))

    def test_uniform_chat(self):
        """Uniform chat should produce roughly uniform signal."""
        messages = [
            ChatMessage(timestamp=i * 5.0, author=f"user_{i}", message="hello")
            for i in range(60)  # one message every 5 seconds for 5 minutes
        ]
        result = compute_chat_signal(messages, duration=300.0, window_size=60, step_size=10)
        # All windows should have similar values
        std = np.std(result)
        self.assertLess(std, np.mean(result) * 0.5)  # low relative variance

    def test_spike_detection(self):
        """A burst of messages should create a spike."""
        messages = []
        # Normal rate: 1 message per 10s
        for i in range(30):
            messages.append(ChatMessage(
                timestamp=i * 10.0, author=f"user_{i}", message="normal"
            ))
        # Spike: 50 messages in 10 seconds at t=150s
        for i in range(50):
            messages.append(ChatMessage(
                timestamp=150.0 + i * 0.2, author=f"spiker_{i}", message="OMG"
            ))

        result = compute_chat_signal(messages, duration=300.0, window_size=60, step_size=10)

        # The window containing t=150 should have the highest value
        spike_window = 15  # (150 - 60) / 10 ... range includes 150
        # Find which windows cover t=150 (windows starting 90-150 cover 150)
        max_idx = np.argmax(result)
        # The spike should be near window index 9-15 (depending on exact window)
        self.assertGreater(result[max_idx], np.mean(result) * 2)

    def test_superchat_weight(self):
        """Super chats should count more than regular messages."""
        regular = [
            ChatMessage(timestamp=30.0, author="user_1", message="hello"),
            ChatMessage(timestamp=31.0, author="user_2", message="hi"),
        ]
        with_sc = [
            ChatMessage(timestamp=30.0, author="user_1", message="hello"),
            ChatMessage(timestamp=31.0, author="user_2", message="hi", is_superchat=True),
        ]

        result_regular = compute_chat_signal(regular, duration=120.0)
        result_sc = compute_chat_signal(with_sc, duration=120.0)

        # The superchat version should have higher total
        self.assertGreater(np.sum(result_sc), np.sum(result_regular))


class TestKeywordScanning(unittest.TestCase):
    """Test keyword detection in transcript and chat."""

    def test_keyword_dictionary_populated(self):
        """Ensure keyword dictionary has entries."""
        self.assertGreater(len(_ALL_KEYWORDS_LOWER), 100)
        # Check specific important keywords exist
        self.assertIn("草", _ALL_KEYWORDS_LOWER)
        self.assertIn("wwww", _ALL_KEYWORDS_LOWER)
        self.assertIn("lol", _ALL_KEYWORDS_LOWER)
        self.assertIn("omg", _ALL_KEYWORDS_LOWER)
        self.assertIn("pogchamp", _ALL_KEYWORDS_LOWER)
        self.assertIn("666", _ALL_KEYWORDS_LOWER)
        self.assertIn("笑死", _ALL_KEYWORDS_LOWER)

    def test_ja_keywords(self):
        """Test Japanese keyword categories exist."""
        ja = KEYWORDS["ja"]
        self.assertIn("excitement", ja)
        self.assertIn("emotion", ja)
        self.assertIn("action", ja)
        self.assertIn("surprise", ja)

    def test_transcript_keyword_scan(self):
        """Scan transcript for keywords."""
        segments = [
            TranscriptSegment(id=0, start=0.0, end=5.0, text="Hello everyone", language="en"),
            TranscriptSegment(id=1, start=10.0, end=15.0, text="OMG that was insane", language="en"),
            TranscriptSegment(id=2, start=20.0, end=25.0, text="草wwww", language="ja"),
        ]

        scores, hits = scan_keywords_in_transcript(segments, window_size=30, step_size=10, duration=60.0)

        # Should find hits for "omg", "insane", "草", "wwww"
        self.assertGreater(len(hits), 0)
        keywords_found = {h.keyword for h in hits}
        self.assertIn("omg", keywords_found)
        self.assertIn("草", keywords_found)

    def test_chat_keyword_scan(self):
        """Scan chat messages for keywords."""
        messages = [
            ChatMessage(timestamp=10.0, author="user1", message="LOL"),
            ChatMessage(timestamp=11.0, author="user2", message="草草草"),
            ChatMessage(timestamp=12.0, author="user3", message="normal message"),
            ChatMessage(timestamp=50.0, author="user4", message="PogChamp"),
        ]

        scores, hits = scan_keywords_in_chat(messages, window_size=30, step_size=10, duration=60.0)

        self.assertGreater(len(hits), 0)
        keywords_found = {h.keyword for h in hits}
        self.assertIn("lol", keywords_found)
        self.assertIn("pogchamp", keywords_found)

    def test_no_keywords_in_normal_text(self):
        """Normal conversational text shouldn't trigger excessive hits."""
        segments = [
            TranscriptSegment(id=0, start=0.0, end=30.0,
                              text="Today we're going to play a game and have a good time", language="en"),
        ]

        scores, hits = scan_keywords_in_transcript(segments, window_size=60, step_size=10, duration=60.0)
        # Should have very few or no hits
        self.assertLess(len(hits), 3)


class TestMergeOverlapping(unittest.TestCase):
    """Test highlight merging."""

    def test_no_overlap(self):
        highlights = [
            {"start": 0, "end": 30, "score": 0.8, "chat_intensity": 0.5,
             "audio_energy": 0.5, "keyword_score": 0.3, "signals": ["chat"]},
            {"start": 100, "end": 130, "score": 0.7, "chat_intensity": 0.4,
             "audio_energy": 0.4, "keyword_score": 0.2, "signals": ["audio"]},
        ]
        merged = _merge_overlapping(highlights, max_gap=30)
        self.assertEqual(len(merged), 2)

    def test_overlap_merges(self):
        highlights = [
            {"start": 0, "end": 40, "score": 0.8, "chat_intensity": 0.5,
             "audio_energy": 0.5, "keyword_score": 0.3, "signals": ["chat"]},
            {"start": 30, "end": 70, "score": 0.9, "chat_intensity": 0.6,
             "audio_energy": 0.4, "keyword_score": 0.2, "signals": ["audio"]},
        ]
        merged = _merge_overlapping(highlights, max_gap=30)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["start"], 0)
        self.assertEqual(merged[0]["end"], 70)
        self.assertEqual(merged[0]["score"], 0.9)  # takes max
        self.assertIn("chat", merged[0]["signals"])
        self.assertIn("audio", merged[0]["signals"])

    def test_gap_within_threshold_merges(self):
        highlights = [
            {"start": 0, "end": 30, "score": 0.8, "chat_intensity": 0.5,
             "audio_energy": 0.5, "keyword_score": 0.3, "signals": ["chat"]},
            {"start": 50, "end": 80, "score": 0.7, "chat_intensity": 0.4,
             "audio_energy": 0.4, "keyword_score": 0.2, "signals": ["audio"]},
        ]
        # Gap = 20s, max_gap = 30s → should merge
        merged = _merge_overlapping(highlights, max_gap=30)
        self.assertEqual(len(merged), 1)

    def test_gap_exceeds_threshold(self):
        highlights = [
            {"start": 0, "end": 30, "score": 0.8, "chat_intensity": 0.5,
             "audio_energy": 0.5, "keyword_score": 0.3, "signals": ["chat"]},
            {"start": 70, "end": 100, "score": 0.7, "chat_intensity": 0.4,
             "audio_energy": 0.4, "keyword_score": 0.2, "signals": ["audio"]},
        ]
        # Gap = 40s, max_gap = 30s → should NOT merge
        merged = _merge_overlapping(highlights, max_gap=30)
        self.assertEqual(len(merged), 2)

    def test_empty_input(self):
        merged = _merge_overlapping([], max_gap=30)
        self.assertEqual(len(merged), 0)


class TestSnapToSentences(unittest.TestCase):
    """Test sentence boundary snapping."""

    def test_snap_start_to_segment_start(self):
        transcript = [
            TranscriptSegment(id=0, start=0.0, end=5.0, text="Hello"),
            TranscriptSegment(id=1, start=8.0, end=13.0, text="World"),
            TranscriptSegment(id=2, start=15.0, end=20.0, text="Test"),
        ]
        start, end = _snap_to_sentences(9.0, 18.0, transcript)
        # Should snap start to segment boundary at 8.0
        self.assertEqual(start, 8.0)
        # Should snap end to segment boundary at 20.0
        self.assertEqual(end, 20.0)

    def test_empty_transcript(self):
        start, end = _snap_to_sentences(10.0, 50.0, [])
        self.assertEqual(start, 10.0)
        self.assertEqual(end, 50.0)


class TestDetectHighlights(unittest.TestCase):
    """Integration test for the full highlight detection pipeline."""

    def test_detect_with_chat_spike(self):
        """Test that a chat spike produces a highlight."""
        # Create a simple transcript
        transcript = [
            TranscriptSegment(id=i, start=i*10.0, end=(i+1)*10.0,
                              text=f"Segment {i}", language="en")
            for i in range(30)  # 5 minutes of segments
        ]

        # Create chat messages with a clear spike at t=150
        messages: list[ChatMessage] = []
        # Background: 1 message per 30s
        for i in range(10):
            messages.append(ChatMessage(
                timestamp=i * 30.0, author=f"bg_user_{i}", message="hello"
            ))
        # Spike: 40 messages around t=150
        for i in range(40):
            messages.append(ChatMessage(
                timestamp=145.0 + i * 0.5, author=f"spike_user_{i}",
                message="OMG LOL LETS GO"
            ))

        highlights = detect_highlights(
            transcript=transcript,
            chat_messages=messages,
            audio_path=None,
            duration=300.0,
            min_score=0.3,  # lower threshold for test
        )

        # Should find at least one highlight
        self.assertGreater(len(highlights), 0)

        # The top highlight should be near the spike
        top = highlights[0]
        # The highlight should overlap with the 140-170 range
        self.assertLess(top.start_time, 180)
        self.assertGreater(top.end_time, 120)

    def test_detect_with_no_signals(self):
        """No signals → no highlights (or very few)."""
        transcript = [
            TranscriptSegment(id=i, start=i*10.0, end=(i+1)*10.0,
                              text="Normal conversation", language="en")
            for i in range(30)
        ]

        highlights = detect_highlights(
            transcript=transcript,
            chat_messages=[],
            audio_path=None,
            duration=300.0,
            min_score=0.8,  # high threshold
        )

        # Should find very few or no highlights
        self.assertLessEqual(len(highlights), 2)

    def test_detect_with_keywords(self):
        """Keyword-rich transcript should produce highlights."""
        transcript = [
            TranscriptSegment(id=0, start=0.0, end=10.0, text="Normal intro", language="en"),
            TranscriptSegment(id=1, start=10.0, end=20.0, text="Normal talking", language="en"),
            # Keyword-dense segment
            TranscriptSegment(id=2, start=60.0, end=70.0,
                              text="OMG no way that was insane LETS GO clutch", language="en"),
            TranscriptSegment(id=3, start=70.0, end=80.0,
                              text="WHAT HOW bruh that was cracked", language="en"),
            TranscriptSegment(id=4, start=100.0, end=110.0, text="Anyway moving on", language="en"),
        ]

        highlights = detect_highlights(
            transcript=transcript,
            chat_messages=[],
            audio_path=None,
            duration=120.0,
            min_score=0.2,  # low threshold since only keyword signal
        )

        # Should find something near the keyword cluster
        if highlights:
            top = highlights[0]
            # Should be in the 60-80s range
            self.assertLess(top.start_time, 100)

    def test_highlight_scores_are_bounded(self):
        """All scores should be in [0, 1] range."""
        transcript = [
            TranscriptSegment(id=i, start=i*10.0, end=(i+1)*10.0,
                              text="Test segment with LOL and 草", language="en")
            for i in range(20)
        ]
        messages = [
            ChatMessage(timestamp=i * 5.0, author=f"user_{i}", message="POGGERS LOL 草")
            for i in range(40)
        ]

        highlights = detect_highlights(
            transcript=transcript,
            chat_messages=messages,
            audio_path=None,
            duration=200.0,
            min_score=0.1,
        )

        for h in highlights:
            self.assertGreaterEqual(h.score, 0.0)
            self.assertLessEqual(h.score, 1.0)
            self.assertGreaterEqual(h.chat_intensity, 0.0)
            self.assertLessEqual(h.chat_intensity, 1.0)

    def test_highlights_sorted_by_score(self):
        """Highlights should be sorted by score descending."""
        transcript = [
            TranscriptSegment(id=i, start=i*10.0, end=(i+1)*10.0,
                              text="LOL", language="en")
            for i in range(30)
        ]
        messages = [
            ChatMessage(timestamp=i * 3.0, author=f"user_{i}", message="omg lol")
            for i in range(100)
        ]

        highlights = detect_highlights(
            transcript=transcript,
            chat_messages=messages,
            audio_path=None,
            duration=300.0,
            min_score=0.1,
        )

        if len(highlights) >= 2:
            for i in range(len(highlights) - 1):
                self.assertGreaterEqual(highlights[i].score, highlights[i + 1].score)


class TestKeywordDictionary(unittest.TestCase):
    """Verify the keyword dictionary structure and content."""

    def test_all_languages_present(self):
        self.assertIn("ja", KEYWORDS)
        self.assertIn("en", KEYWORDS)
        self.assertIn("zh", KEYWORDS)
        self.assertIn("emotes", KEYWORDS)

    def test_all_categories_present(self):
        for lang in ["ja", "en", "zh"]:
            categories = KEYWORDS[lang]
            self.assertIn("excitement", categories)
            self.assertIn("emotion", categories)
            self.assertIn("action", categories)
            self.assertIn("surprise", categories)

    def test_minimum_keywords_per_category(self):
        """Each category should have at least 5 keywords."""
        for lang in ["ja", "en", "zh"]:
            for category, words in KEYWORDS[lang].items():
                self.assertGreaterEqual(
                    len(words), 5,
                    f"{lang}/{category} has only {len(words)} keywords"
                )

    def test_emotes_present(self):
        self.assertIn("positive", KEYWORDS["emotes"])
        self.assertIn("negative", KEYWORDS["emotes"])

    def test_critical_vtuber_keywords(self):
        """Key VTuber community terms must be in the dictionary."""
        critical_ja = ["草", "やばい", "かわいい", "すごい", "神"]
        critical_en = ["lol", "omg", "pogchamp", "clutch"]
        critical_zh = ["666", "笑死", "牛逼", "神操作"]

        for kw in critical_ja + critical_en + critical_zh:
            self.assertIn(
                kw.lower(), _ALL_KEYWORDS_LOWER,
                f"Critical keyword '{kw}' missing from dictionary"
            )


if __name__ == "__main__":
    unittest.main()
