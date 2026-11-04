from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_settings
from app.coros import oauth
from app.coros.models import CorosAccount
from app.db import get_db
from app.worker import enqueue_sync, sync_lock

router = APIRouter(prefix="/coros", tags=["coros"])
LOCAL_REDIRECT = "http://localhost:8765/callback"


class CorosStatus(BaseModel):
    """Connection and sync state shown in Settings."""

    status: str
    syncing: bool
    last_sync_at: datetime | None
    last_sync_status: dict | None
    redirect_uri: str


class CompleteIn(BaseModel):
    """Redirect URL pasted by the user when the callback could not reach the app."""

    url: str


def _public_url() -> str | None:
    """Externally reachable app URL (Tailscale HTTPS), if configured."""
    return get_settings().public_url


def _redirect_uri() -> str:
    """Where COROS sends the browser after login."""
    public = _public_url()
    return f"{public.rstrip('/')}/api/coros/callback" if public else LOCAL_REDIRECT


@router.get("/status", response_model=CorosStatus)
def coros_status(db: Session = Depends(get_db)):
    """Connection status and last sync result."""
    account = db.get(CorosAccount, 1)
    return CorosStatus(
        status=account.status if account else "disconnected",
        syncing=sync_lock().is_held(),
        last_sync_at=account.last_sync_at if account else None,
        last_sync_status=account.last_sync_status if account else None,
        redirect_uri=_redirect_uri(),
    )


@router.post("/connect")
def connect(db: Session = Depends(get_db)) -> dict[str, str]:
    """Start the COROS login; the client opens the returned URL."""
    try:
        url = oauth.start_connect(db, get_settings().coros_server_url, _redirect_uri())
    except oauth.OAuthError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error
    return {"authorize_url": url}


def _finish(db: Session, url: str) -> None:
    """Complete the login and kick off the first sync."""
    oauth.finish_connect(db, url)
    enqueue_sync()


@router.get("/callback")
def callback(request: Request, db: Session = Depends(get_db)):
    """OAuth redirect target when the app is reachable from the browser (Tailscale HTTPS)."""
    try:
        _finish(db, str(request.url))
    except oauth.OAuthError as error:
        return RedirectResponse(f"/settings?coros_error={quote(str(error))}")
    return RedirectResponse("/settings?coros=connected")


@router.post("/complete")
def complete(data: CompleteIn, db: Session = Depends(get_db)) -> dict[str, str]:
    """Finish the login from a pasted redirect URL."""
    try:
        _finish(db, data.url)
    except oauth.OAuthError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error
    return {"status": "connected"}


@router.post("/sync", status_code=status.HTTP_202_ACCEPTED)
def sync_now(db: Session = Depends(get_db)) -> dict[str, str]:
    """Queue a sync now."""
    account = db.get(CorosAccount, 1)
    if account is None or account.status != "connected":
        raise HTTPException(status.HTTP_409_CONFLICT, "COROS is not connected")
    if sync_lock().is_held():
        raise HTTPException(status.HTTP_409_CONFLICT, "A sync is already running")
    enqueue_sync()
    return {"status": "queued"}
