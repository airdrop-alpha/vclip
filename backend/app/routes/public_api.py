"""
VClip Public API v1 — authenticated REST endpoints with x402 micropayments.

All routes under /api/v1/* that require an API key for access.
x402 micropayment headers are added to clip-related responses.

Phase 5 feature.

x402 spec: https://x402.org
- 402 Payment Required response includes payment details
- Client sends payment proof in X-Payment header
- Server verifies and processes
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response

from app.config import settings
from app.db import (
    create_api_key,
    get_user_by_id,
    list_api_keys,
    log_usage,
)
from app.middleware.api_key import generate_api_key, get_api_key_info, require_api_key
from app.middleware.rate_limit import check_rate_limit
from app.models import ApiKeyCreate, ApiKeyResponse
from app.routes.auth import require_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["public-api"])


# ── x402 helpers ──────────────────────────────────────────────────

def _x402_headers(
    resource: str,
    price_usd: float,
    response: Response,
) -> None:
    """
    Add x402 micropayment headers to a response.

    These headers follow the x402 draft specification, advertising
    that the resource can be paid for micropayments on-chain.

    Headers added:
      X-Payment-Required: true
      X-Payment-Amount: 0.05 USD
      X-Payment-Network: base-sepolia
      X-Payment-Address: 0x...
      X-Payment-Resource: /api/v1/jobs/xxx/clips/yyy/download
    """
    if not settings.x402_wallet_address:
        return
    response.headers["X-Payment-Required"] = "true"
    response.headers["X-Payment-Amount"] = f"{price_usd:.4f} USD"
    response.headers["X-Payment-Network"] = settings.x402_network
    response.headers["X-Payment-Address"] = settings.x402_wallet_address
    response.headers["X-Payment-Resource"] = resource


def _add_payment_required_headers(response: Response, resource: str) -> None:
    """Attach x402 payment info to clip responses."""
    _x402_headers(resource, settings.x402_price_per_clip, response)


# ── API Key management ────────────────────────────────────────────

@router.post("/keys", response_model=ApiKeyResponse, status_code=201)
async def create_key(
    body: ApiKeyCreate,
    user: dict = Depends(require_current_user),
):
    """
    Create a new API key for the authenticated user.

    The plain key is shown only once in the response.
    Store it securely — it cannot be recovered.
    """
    plain_key, key_hash, key_prefix = generate_api_key()
    key_id = await create_api_key(
        user_id=user["id"],
        name=body.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
    )
    logger.info(f"API key created: {key_id} for user {user['id']}")
    return ApiKeyResponse(
        key_id=key_id,
        name=body.name,
        key=plain_key,  # Only shown once
        created_at="",
    )


@router.get("/keys", response_model=list[ApiKeyResponse])
async def list_keys(user: dict = Depends(require_current_user)):
    """List API keys for the current user (keys are redacted)."""
    rows = await list_api_keys(user["id"])
    return [
        ApiKeyResponse(
            key_id=r["key_id"],
            name=r["name"],
            created_at=r["created_at"],
            last_used=r.get("last_used"),
        )
        for r in rows
    ]


# ── Public job submission (API key auth) ──────────────────────────

@router.post("/process")
async def submit_job_api(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    key_record: dict = Depends(require_api_key),
):
    """
    **Public API**: Submit a clipping job using an API key.

    This is the programmatic interface for the VClip API.
    Rate limited to {rate_limit_rpm} requests/minute per key.

    Returns the same job_id as the standard endpoint.
    """
    # Rate limiting
    await check_rate_limit(request, api_key_id=key_record.get("key_id"), cost=5.0)

    body = await request.json()
    url = body.get("url", "")
    options_raw = body.get("options", {})

    from app.models import JobCreateRequest, JobOptions
    from app.routes.jobs import _validate_video_url

    if not _validate_video_url(url):
        raise HTTPException(status_code=400, detail="Invalid video URL")

    try:
        options = JobOptions(**options_raw) if options_raw else JobOptions()
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid options: {e}")

    from app.db import create_job
    job_req = JobCreateRequest(url=url, options=options)
    user_id = key_record.get("user_id")
    job_id = await create_job(job_req, user_id=user_id)

    from app.workers.pipeline import run_pipeline_with_retry
    background_tasks.add_task(run_pipeline_with_retry, job_id, url, options)

    # Log usage
    client_ip = request.client.host if request.client else ""
    await log_usage(
        endpoint="/api/v1/process",
        ip_address=client_ip,
        user_id=user_id,
        api_key_id=key_record.get("key_id"),
        job_id=job_id,
    )

    # Add x402 headers (the clip download will cost $0.05)
    _add_payment_required_headers(
        response, f"/api/v1/jobs/{job_id}/export"
    )

    return {
        "job_id": job_id,
        "status": "pending",
        "payment_info": {
            "cost_per_clip": settings.x402_price_per_clip,
            "currency": "USD",
            "network": settings.x402_network,
            "wallet": settings.x402_wallet_address or "not configured",
        } if settings.x402_wallet_address else None,
    }


# ── Rate-limit test endpoint ──────────────────────────────────────

@router.get("/ping")
async def ping(
    request: Request,
    key_record: Optional[dict] = Depends(get_api_key_info),
):
    """
    API health ping — returns 200 with rate limit headers.

    No API key required for this endpoint.
    """
    client_ip = request.client.host if request.client else "unknown"
    return {
        "pong": True,
        "api_version": "1.0.0",
        "authenticated": key_record is not None,
        "x402_enabled": bool(settings.x402_wallet_address),
        "platforms": ["youtube", "bilibili", "twitch"],
    }
