"""
VClip API key authentication — FastAPI dependency.

API keys have the format:  vclip_<32-char-hex>
They are hashed with SHA-256 before storage and looked up by hash on each request.

Phase 5 feature.
"""
from __future__ import annotations

import hashlib
import logging
import secrets
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import settings
from app.db import get_api_key_by_hash, update_api_key_last_used

logger = logging.getLogger(__name__)

_API_KEY_HEADER = APIKeyHeader(name=settings.api_key_header, auto_error=False)


def generate_api_key() -> tuple[str, str]:
    """
    Generate a new API key.

    Returns:
        (plain_key, key_hash) — plain_key is shown once to the user,
        key_hash is stored in the DB.
    """
    raw = secrets.token_hex(32)
    plain = f"vclip_{raw}"
    key_hash = _hash_key(plain)
    key_prefix = plain[:12]  # "vclip_" + first 6 hex chars — for display
    return plain, key_hash, key_prefix


def _hash_key(plain_key: str) -> str:
    """SHA-256 hash of a plain API key for secure storage."""
    return hashlib.sha256(plain_key.encode()).hexdigest()


async def get_api_key_info(
    api_key: Optional[str] = Security(_API_KEY_HEADER),
) -> Optional[dict]:
    """
    FastAPI dependency: validate an API key header and return the key record.

    Returns None if no key provided (allows anonymous access on public routes).
    Raises 401 if key is provided but invalid.
    """
    if not api_key:
        return None

    key_hash = _hash_key(api_key)
    key_record = await get_api_key_by_hash(key_hash)

    if key_record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": f"ApiKey realm=\"{settings.api_key_header}\""},
        )

    # Update last-used timestamp (fire and forget)
    try:
        await update_api_key_last_used(key_record["key_id"])
    except Exception as e:
        logger.debug(f"Failed to update last_used: {e}")

    return key_record


async def require_api_key(
    key_record: Optional[dict] = Depends(get_api_key_info),
) -> dict:
    """Like get_api_key_info but raises 401 if no key provided."""
    if key_record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Include X-API-Key header.",
        )
    return key_record
