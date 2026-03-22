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
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

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
    highlight_window_size: int = 60  # seconds
    highlight_step_size: int = 10  # seconds
    highlight_min_score: float = 0.6
    highlight_max_gap: int = 30  # seconds for merging
    highlight_buffer: int = 5  # ±seconds around clip boundaries

    # Weights for composite scoring
    weight_chat: float = 0.45
    weight_audio: float = 0.30
    weight_keyword: float = 0.25

    # Clip generation
    default_aspect_ratio: str = "16:9"
    clip_max_duration: int = 120  # seconds
    clip_min_duration: int = 15  # seconds
    video_codec: str = "libx264"
    video_crf: int = 23
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"

    def ensure_dirs(self) -> None:
        """Create all required directories."""
        for d in [self.data_dir, self.temp_dir, self.clips_dir]:
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
