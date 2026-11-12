from urllib.parse import quote, urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.strava import client
from app.strava.export import SendResult, send_workout
from app.workouts import service as workouts

router = APIRouter(tags=["strava"])
LOCAL_REDIRECT = "http://localhost/api/strava/callback"


class StravaStatus(BaseModel):
    """What Settings needs to guide the setup."""

    has_credentials: bool
    connected: bool
    athlete_name: str | None
    callback_domain: str  # what to enter as "Authorization Callback Domain" on Strava


class CredentialsIn(BaseModel):
    """The user's Strava API application keys."""

    client_id: str = Field(pattern=r"^\d{1,20}$")
    client_secret: str = Field(min_length=10, max_length=100)


class CompleteIn(BaseModel):
    """Redirect URL pasted by the user when the callback could not reach the app."""

    url: str


def _redirect_uri() -> str:
    """Callback on the public (Tailscale) URL if configured, else localhost to paste back."""
    public = get_settings().public_url
    return f"{public.rstrip('/')}/api/strava/callback" if public else LOCAL_REDIRECT


def _bad_request(error: client.StravaError) -> HTTPException:
    """Strava problems as 502 when Strava itself failed, else 400 (setup, login, request)."""
    down = isinstance(error, client.StravaUnavailable)
    code = status.HTTP_502_BAD_GATEWAY if down else status.HTTP_400_BAD_REQUEST
    return HTTPException(code, str(error))


@router.get("/strava/status", response_model=StravaStatus)
def strava_status(db: Session = Depends(get_db)):
    """Setup and connection state."""
    account = client.get_account(db)
    return StravaStatus(
        has_credentials=bool(account.client_id and account.client_secret),
        connected=bool(account.refresh_token),
        athlete_name=account.athlete_name,
        callback_domain=urlparse(_redirect_uri()).hostname or "localhost",
    )


@router.put("/strava/credentials", status_code=status.HTTP_204_NO_CONTENT)
def put_credentials(data: CredentialsIn, db: Session = Depends(get_db)) -> None:
    """Save the API application keys (disconnects any previous login)."""
    client.save_credentials(db, data.client_id, data.client_secret)


@router.post("/strava/connect")
def connect(db: Session = Depends(get_db)) -> dict[str, str]:
    """Start the Strava login; the client opens the returned URL."""
    try:
        return {"authorize_url": client.start_connect(db, _redirect_uri())}
    except client.StravaError as error:
        raise _bad_request(error) from error


@router.get("/strava/callback")
def callback(request: Request, db: Session = Depends(get_db)):
    """OAuth redirect target when the app is reachable from the browser (PUBLIC_URL)."""
    try:
        client.finish_connect(db, str(request.url))
    except client.StravaError as error:
        return RedirectResponse(f"/settings?strava_error={quote(str(error))}")
    return RedirectResponse("/settings?strava=connected")


@router.post("/strava/complete")
def complete(data: CompleteIn, db: Session = Depends(get_db)) -> dict[str, str]:
    """Finish the login from a pasted redirect URL."""
    try:
        client.finish_connect(db, data.url)
    except client.StravaError as error:
        raise _bad_request(error) from error
    return {"status": "connected"}


@router.post("/strava/disconnect", status_code=status.HTTP_204_NO_CONTENT)
def disconnect(db: Session = Depends(get_db)) -> None:
    """Forget the Strava login."""
    client.disconnect(db)


@router.post("/workouts/{workout_id}/strava", response_model=SendResult)
def send_to_strava(workout_id: int, db: Session = Depends(get_db)):
    """Add the workout to Strava: describe the watch activity, or create a new one."""
    workout = workouts.get_workout(db, workout_id)
    if workout is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workout not found")
    try:
        return send_workout(db, workout)
    except client.StravaError as error:
        raise _bad_request(error) from error
