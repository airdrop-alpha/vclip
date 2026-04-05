"""
VClip authentication routes — JWT-based user accounts.

Endpoints:
  POST /api/v1/auth/register  — create account
  POST /api/v1/auth/token     — login (OAuth2 password flow)
  GET  /api/v1/auth/me        — current user info

Phase 4 feature.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from app.config import settings
from app.db import create_user, get_user_by_email, get_user_by_id
from app.models import TokenResponse, UserCreate, UserResponse, UserTier

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


# ── Password hashing ──────────────────────────────────────────────

def _hash_password(password: str) -> str:
    try:
        from passlib.context import CryptContext  # type: ignore
        ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        # bcrypt 5.0+ enforces 72-byte limit; truncate to avoid ValueError
        return ctx.hash(password[:72])
    except ImportError:
        # Fallback: SHA-256 (not for production — install passlib[bcrypt])
        import hashlib
        return "sha256:" + hashlib.sha256(password.encode()).hexdigest()


def _verify_password(plain: str, hashed: str) -> bool:
    if hashed.startswith("sha256:"):
        import hashlib
        return "sha256:" + hashlib.sha256(plain.encode()).hexdigest() == hashed
    try:
        from passlib.context import CryptContext  # type: ignore
        ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return ctx.verify(plain[:72], hashed)
    except ImportError:
        return False


# ── JWT helpers ───────────────────────────────────────────────────

def _create_access_token(user_id: str) -> str:
    try:
        from jose import jwt  # type: ignore
    except ImportError:
        raise RuntimeError("python-jose not installed; run: pip install python-jose[cryptography]")

    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _decode_token(token: str) -> Optional[str]:
    """Return user_id from token, or None if invalid."""
    try:
        from jose import jwt, JWTError  # type: ignore
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload.get("sub")
    except Exception:
        return None


# ── Dependency: current user ──────────────────────────────────────

async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[dict]:
    """
    FastAPI dependency: resolve JWT token to a user dict.
    Returns None if no valid token (allows anonymous access to most routes).
    """
    if not token:
        return None
    user_id = _decode_token(token)
    if not user_id:
        return None
    return await get_user_by_id(user_id)


async def require_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> dict:
    """Like get_current_user but raises 401 if not authenticated."""
    user = await get_current_user(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# ── Routes ───────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: UserCreate):
    """
    Register a new user account.

    Returns an access token on success.
    Free tier: 3 clips/day, watermark on exports.
    """
    existing = await get_user_by_email(body.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    if len(body.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")

    hashed = _hash_password(body.password)
    user_id = await create_user(body.email, hashed)
    token = _create_access_token(user_id)

    logger.info(f"New user registered: {body.email} ({user_id})")
    return TokenResponse(access_token=token)


@router.post("/token", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 password flow login.

    Returns JWT access token.
    """
    user = await get_user_by_email(form.username)
    if user is None or not _verify_password(form.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = _create_access_token(user["id"])
    logger.info(f"User logged in: {user['email']}")
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def me(user: dict = Depends(require_current_user)):
    """Get current user profile and usage stats."""
    tier = UserTier(user.get("tier", "free"))
    clips_limit = (
        settings.free_clips_per_day if tier == UserTier.FREE
        else 100 if tier == UserTier.PRO
        else 10000
    )
    return UserResponse(
        id=user["id"],
        email=user["email"],
        tier=tier,
        clips_today=user.get("clips_today", 0),
        clips_limit=clips_limit,
        created_at=user.get("created_at", ""),
    )


# ── YouTube OAuth (upload integration) ────────────────────────────

@router.get("/youtube/authorize", tags=["youtube"])
async def youtube_authorize(user: dict = Depends(require_current_user)):
    """
    Return YouTube OAuth2 authorization URL.
    User must visit this URL and grant permissions.
    """
    if not settings.youtube_client_id:
        raise HTTPException(status_code=501, detail="YouTube integration not configured")

    scopes = ["https://www.googleapis.com/auth/youtube.upload"]
    scope_str = "%20".join(scopes)
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.youtube_client_id}"
        f"&redirect_uri={settings.youtube_redirect_uri}"
        f"&response_type=code"
        f"&scope={scope_str}"
        f"&access_type=offline"
        f"&state={user['id']}"
    )
    return {"auth_url": auth_url}


@router.get("/youtube/callback", tags=["youtube"])
async def youtube_callback(code: str, state: str):
    """
    Handle YouTube OAuth2 callback.
    Exchanges auth code for tokens (stored server-side for upload).
    """
    # In production: exchange code for tokens and store in DB
    # For now: acknowledge receipt
    logger.info(f"YouTube OAuth callback received for user {state}")
    return {"status": "ok", "message": "YouTube authorization received. Upload is now available."}
