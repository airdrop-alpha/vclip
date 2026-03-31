"""
VClip YouTube upload service — upload generated clips to YouTube.

Uses the YouTube Data API v3 with OAuth2 user tokens.
Requires: google-api-python-client, google-auth

Phase 4 feature.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def upload_to_youtube(
    clip_path: Path,
    title: str,
    description: str = "",
    tags: Optional[list[str]] = None,
    privacy: str = "unlisted",
    access_token: Optional[str] = None,
) -> dict:
    """
    Upload a clip to YouTube via the Data API v3.

    Args:
        clip_path: Path to the MP4 clip file
        title: Video title (max 100 chars)
        description: Video description
        tags: List of tags
        privacy: 'public', 'unlisted', or 'private'
        access_token: OAuth2 access token for the user's YouTube account

    Returns:
        dict with youtube_id, watch_url, and status

    Note:
        Requires google-api-python-client:
            pip install google-api-python-client google-auth
    """
    if not clip_path.exists():
        raise FileNotFoundError(f"Clip file not found: {clip_path}")

    try:
        from googleapiclient.discovery import build  # type: ignore
        from googleapiclient.http import MediaFileUpload  # type: ignore
        from google.oauth2.credentials import Credentials  # type: ignore
    except ImportError:
        logger.warning(
            "google-api-python-client not installed. "
            "Install with: pip install google-api-python-client google-auth"
        )
        return _mock_upload(clip_path, title)

    if not access_token:
        logger.warning("No access_token provided — using mock upload")
        return _mock_upload(clip_path, title)

    creds = Credentials(token=access_token)
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags or ["VTuber", "clip", "highlight"],
            "categoryId": "20",  # Gaming
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        str(clip_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=5 * 1024 * 1024,  # 5MB chunks
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    logger.info(f"Uploading '{title}' to YouTube...")

    while response is None:
        status, response = request.next_chunk()
        if status:
            logger.debug(f"YouTube upload {int(status.progress() * 100)}%")

    video_id = response.get("id", "")
    logger.info(f"YouTube upload complete: https://youtu.be/{video_id}")

    return {
        "youtube_id": video_id,
        "watch_url": f"https://youtu.be/{video_id}",
        "status": "uploaded",
    }


def _mock_upload(clip_path: Path, title: str) -> dict:
    """Return a mock upload response for testing / unconfigured state."""
    logger.info(f"[MOCK] Would upload '{title}' from {clip_path}")
    return {
        "youtube_id": "mock_video_id",
        "watch_url": "https://youtu.be/mock_video_id",
        "status": "mock",
        "note": "Set YOUTUBE_CLIENT_ID + user OAuth token for real uploads",
    }
