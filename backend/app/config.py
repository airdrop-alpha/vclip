"""
VClip configuration — environment variables and defaults.
"""
import os
from pathlib import Path
from pydantic import BaseModel


class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://vclip.pages.dev",
        "https://*.vclip.pages.dev",
        "https://*.trycloudflare.com",
    ]

    # Paths
    data_dir: Path = Path(os.environ.get("VCLIP_DATA_DIR", "./data"))
    db_path: Path = Path(os.environ.get("VCLIP_DB_PATH", "./data/vclip.db"))
    temp_dir: Path = Path(os.environ.get("VCLIP_TEMP_DIR", "./data/tmp"))
    clips_dir: Path = Path(os.environ.get("VCLIP_CLIPS_DIR", "./data/clips"))

    # Whisper / STT
    whisper_model: str = os.environ.get("VCLIP_WHISPER_MODEL", "large-v3")
    whisper_device: str = os.environ.get("VCLIP_WHISPER_DEVICE", "auto")
    whisper_compute_type: str = os.environ.get("VCLIP_WHISPER_COMPUTE", "auto")

    # Highlight detection
    highlight_window_size: int = 60   # seconds
    highlight_step_size: int = 10     # seconds
    highlight_min_score: float = 0.6
    highlight_max_gap: int = 30       # seconds for merging
    highlight_buffer: int = 5         # ±seconds around clip boundaries

    # Weights for composite scoring
    weight_chat: float = 0.45
    weight_audio: float = 0.30
    weight_keyword: float = 0.25

    # Concurrency
    max_concurrent_jobs: int = int(os.environ.get("MAX_CONCURRENT_JOBS", "2"))

    # Clip generation
    default_aspect_ratio: str = "16:9"
    clip_max_duration: int = 120   # seconds
    clip_min_duration: int = 15    # seconds
    video_codec: str = "libx264"
    video_crf: int = 23
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"

    # ── Phase 3: AI / LLM ─────────────────────────────────────
    openai_api_key: str = os.environ.get("OPENAI_API_KEY", "")
    openai_model: str = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    llm_rerank_enabled: bool = os.environ.get("VCLIP_LLM_RERANK", "false").lower() == "true"

    # ── Phase 4: Auth / Monetization ──────────────────────────
    jwt_secret: str = os.environ.get("VCLIP_JWT_SECRET", "change-me-in-production-use-32-bytes")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = int(os.environ.get("VCLIP_JWT_EXPIRE_MINUTES", "10080"))  # 7 days

    # Freemium limits
    free_clips_per_day: int = int(os.environ.get("VCLIP_FREE_CLIPS_DAY", "3"))
    watermark_enabled: bool = os.environ.get("VCLIP_WATERMARK", "true").lower() == "true"
    watermark_text: str = os.environ.get("VCLIP_WATERMARK_TEXT", "Made with VClip")

    # YouTube upload (OAuth2)
    youtube_client_id: str = os.environ.get("YOUTUBE_CLIENT_ID", "")
    youtube_client_secret: str = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
    youtube_redirect_uri: str = os.environ.get("YOUTUBE_REDIRECT_URI", "http://localhost:8000/api/v1/auth/youtube/callback")

    # ── Phase 5: Public API + x402 ────────────────────────────
    api_key_header: str = "X-API-Key"
    # Cost per clip in USD (x402 micropayment)
    x402_price_per_clip: float = float(os.environ.get("VCLIP_X402_PRICE", "0.05"))
    x402_wallet_address: str = os.environ.get("VCLIP_X402_WALLET", "")
    x402_network: str = os.environ.get("VCLIP_X402_NETWORK", "base-sepolia")

    # Rate limiting (requests per minute, per API key / IP)
    rate_limit_rpm: int = int(os.environ.get("VCLIP_RATE_LIMIT_RPM", "60"))
    rate_limit_burst: int = int(os.environ.get("VCLIP_RATE_LIMIT_BURST", "10"))

    def ensure_dirs(self) -> None:
        """Create all required directories."""
        for d in [self.data_dir, self.temp_dir, self.clips_dir]:
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
