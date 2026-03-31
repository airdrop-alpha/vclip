"""
VClip Pydantic models — request/response schemas and internal data structures.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────

class JobStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    TRANSCRIBING = "transcribing"
    PARSING_CHAT = "parsing_chat"
    DETECTING = "detecting"
    CLIPPING = "clipping"
    SUBTITLING = "subtitling"
    COMPLETE = "complete"
    FAILED = "failed"


class HighlightType(str, Enum):
    FUNNY = "funny"
    EXCITING = "exciting"
    EMOTIONAL = "emotional"
    SKILL = "skill"
    MIXED = "mixed"


class AspectRatio(str, Enum):
    LANDSCAPE = "16:9"
    PORTRAIT = "9:16"


class SubtitleStyle(str, Enum):
    ANIME = "anime"
    MODERN = "modern"
    MINIMAL = "minimal"


# ── Phase 4: Tier ─────────────────────────────────────────────

class UserTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


# ── Request models ─────────────────────────────────────────────

class JobOptions(BaseModel):
    languages: list[str] = Field(default=["ja", "en"], description="Language codes for transcription")
    max_clips: int = Field(default=10, ge=1, le=50)
    min_score: float = Field(default=0.6, ge=0.0, le=1.0)
    aspect_ratios: list[AspectRatio] = Field(default=[AspectRatio.LANDSCAPE])
    subtitle_style: SubtitleStyle = Field(default=SubtitleStyle.ANIME)
    burn_subtitles: bool = Field(default=True)
    # Phase 4
    template: str = Field(default="anime", description="Clip template style")
    watermark: bool = Field(default=False, description="Apply watermark (set by server for free tier)")


class JobCreateRequest(BaseModel):
    url: str = Field(..., description="YouTube / Bilibili / Twitch video URL")
    options: JobOptions = Field(default_factory=JobOptions)


# ── Transcript models ─────────────────────────────────────────

class WordTimestamp(BaseModel):
    word: str
    start: float
    end: float
    probability: float = 0.0


class TranscriptSegment(BaseModel):
    id: int = 0
    start: float
    end: float
    text: str
    language: str = "unknown"
    words: list[WordTimestamp] = Field(default_factory=list)


# ── Chat models ────────────────────────────────────────────────

class ChatMessage(BaseModel):
    timestamp: float  # seconds from stream start
    author: str
    message: str
    is_member: bool = False
    is_superchat: bool = False
    amount: Optional[float] = None


# ── Highlight models ──────────────────────────────────────────

class Highlight(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    start_time: float
    end_time: float
    score: float
    highlight_type: HighlightType = HighlightType.MIXED
    description: str = ""
    transcript_snippet: str = ""
    chat_intensity: float = 0.0
    audio_energy: float = 0.0
    keyword_score: float = 0.0
    contributing_signals: list[str] = Field(default_factory=list)
    # Phase 3: AI re-ranking
    llm_explanation: Optional[str] = None
    confidence: Optional[float] = None
    llm_rank: Optional[int] = None


# ── Clip models ────────────────────────────────────────────────

class ClipInfo(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    highlight_id: str
    aspect_ratio: AspectRatio
    file_path: str = ""
    download_url: str = ""
    thumbnail_url: str = ""
    duration: float = 0.0
    has_subtitles: bool = False


# ── Job models ─────────────────────────────────────────────────

class JobMetadata(BaseModel):
    title: str = ""
    channel: str = ""
    duration: float = 0.0
    upload_date: str = ""
    thumbnail_url: str = ""


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: float = 0.0
    message: str = ""
    created_at: str = ""
    updated_at: str = ""
    url: str = ""
    metadata: Optional[JobMetadata] = None
    options: Optional[JobOptions] = None
    highlights: list[Highlight] = Field(default_factory=list)
    clips: list[ClipInfo] = Field(default_factory=list)
    error: Optional[str] = None


class JobCreateResponse(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.PENDING
    estimated_time: Optional[int] = None  # seconds


# ── WebSocket models ──────────────────────────────────────────

class ProgressUpdate(BaseModel):
    job_id: str
    status: JobStatus
    progress: float
    message: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ── Phase 4: Auth / User models ───────────────────────────────

class UserCreate(BaseModel):
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    tier: UserTier = UserTier.FREE
    clips_today: int = 0
    clips_limit: int = 3
    created_at: str = ""


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Phase 5: API Key models ───────────────────────────────────

class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)


class ApiKeyResponse(BaseModel):
    key_id: str
    name: str
    key: Optional[str] = None  # Only shown once on creation
    created_at: str = ""
    last_used: Optional[str] = None


class UsageStats(BaseModel):
    total_jobs: int = 0
    total_clips: int = 0
    jobs_today: int = 0
    clips_today: int = 0
    jobs_by_status: dict[str, int] = Field(default_factory=dict)
    avg_processing_time_seconds: float = 0.0
    top_platforms: dict[str, int] = Field(default_factory=dict)
