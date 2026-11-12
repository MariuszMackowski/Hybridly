"""Strava OAuth (the user's own API application) and the few API calls the export needs."""

import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from sqlalchemy.orm import Session

from app.strava.models import StravaAccount

AUTHORIZE_URL = "https://www.strava.com/oauth/authorize"
TOKEN_URL = "https://www.strava.com/oauth/token"
API_URL = "https://www.strava.com/api/v3"
SCOPES = ("activity:read_all", "activity:write")
REFRESH_MARGIN = timedelta(minutes=5)


class StravaError(Exception):
    """Strava refused a request or is unreachable."""


class StravaUnavailable(StravaError):
    """Strava could not be reached or failed on its side (network error, 5xx)."""


class NotFound(StravaError):
    """The requested Strava object does not exist (e.g. the activity was deleted)."""


class NotConnected(StravaError):
    """No usable tokens: the user has to (re)connect Strava in Settings."""


def _http() -> httpx.Client:
    """HTTP client factory (patch point for tests)."""
    return httpx.Client(timeout=30)


def get_account(db: Session) -> StravaAccount:
    """The single Strava account row, created on first use."""
    account = db.get(StravaAccount, 1)
    if account is None:
        account = StravaAccount(id=1)
        db.add(account)
        db.flush()
    return account


def save_credentials(db: Session, client_id: str, client_secret: str) -> None:
    """Store the user's API application keys; any previous login is dropped."""
    account = get_account(db)
    account.client_id, account.client_secret = client_id.strip(), client_secret.strip()
    _clear_tokens(account)
    db.commit()


def start_connect(db: Session, redirect_uri: str) -> str:
    """Authorization URL for the user's browser."""
    account = get_account(db)
    if not account.client_id or not account.client_secret:
        raise NotConnected("Save your Strava Client ID and Client Secret first.")
    account.pending_state = secrets.token_urlsafe(16)
    db.commit()
    query = {
        "client_id": account.client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "approval_prompt": "auto",
        "scope": ",".join(SCOPES),
        "state": account.pending_state,
    }
    return f"{AUTHORIZE_URL}?{urlencode(query)}"


def _token_request(account: StravaAccount, form: dict) -> dict:
    """POST to the token endpoint with the app credentials; raises on failure."""
    try:
        with _http() as http:
            response = http.post(
                TOKEN_URL,
                data={
                    **form,
                    "client_id": account.client_id,
                    "client_secret": account.client_secret,
                },
            )
    except httpx.HTTPError as error:
        raise StravaUnavailable(f"Strava is not reachable: {error}") from error
    if response.status_code in (400, 401):
        raise NotConnected(f"Strava rejected the login ({response.status_code}): {response.text}")
    if response.status_code >= 500:
        raise StravaUnavailable(f"Strava token request failed: {response.status_code}")
    if response.status_code >= 400:
        raise StravaError(f"Strava token request failed: {response.status_code}")
    return response.json()


def _store_tokens(account: StravaAccount, payload: dict) -> None:
    """Save a token response (Strava may rotate the refresh token)."""
    account.access_token = payload["access_token"]
    account.refresh_token = payload.get("refresh_token", account.refresh_token)
    account.expires_at = datetime.fromtimestamp(int(payload["expires_at"]), UTC)


def finish_connect(db: Session, callback_url: str) -> None:
    """Exchange the code from the redirect URL (callback or pasted) for tokens."""
    account = get_account(db)
    query = {k: v[0] for k, v in parse_qs(urlparse(callback_url.strip()).query).items()}
    if "error" in query:
        raise StravaError(f"Strava refused access: {query['error']}")
    if not account.pending_state or query.get("state") != account.pending_state:
        raise StravaError("Login link expired or does not match — start the connection again.")
    granted = set(query.get("scope", "").split(","))
    if missing := [s for s in SCOPES if s not in granted]:
        raise StravaError(f"Allow all requested permissions (missing: {', '.join(missing)}).")
    payload = _token_request(
        account, {"grant_type": "authorization_code", "code": query.get("code", "")}
    )
    _store_tokens(account, payload)
    athlete = payload.get("athlete") or {}
    account.athlete_name = " ".join(
        filter(None, [athlete.get("firstname"), athlete.get("lastname")])
    )
    account.pending_state = None
    db.commit()


def _clear_tokens(account: StravaAccount) -> None:
    """Drop the login (tokens and athlete) but keep the API app keys."""
    account.access_token = account.refresh_token = account.expires_at = None
    account.athlete_name = None


def disconnect(db: Session) -> None:
    """Forget the tokens (the API app keys stay)."""
    _clear_tokens(get_account(db))
    db.commit()


def access_token(db: Session) -> str:
    """A valid access token, refreshed when close to expiry."""
    account = get_account(db)
    if not account.refresh_token:
        raise NotConnected("Strava is not connected — connect it in Settings.")
    if account.expires_at and account.expires_at - datetime.now(UTC) > REFRESH_MARGIN:
        return account.access_token
    try:
        payload = _token_request(
            account, {"grant_type": "refresh_token", "refresh_token": account.refresh_token}
        )
    except NotConnected:
        disconnect(db)
        raise
    _store_tokens(account, payload)
    db.commit()
    return account.access_token


def api(db: Session, method: str, path: str, **kwargs) -> dict | list:
    """Call the Strava API with a fresh token; raises StravaError with Strava's message."""
    headers = {"Authorization": f"Bearer {access_token(db)}"}
    try:
        with _http() as http:
            response = http.request(method, f"{API_URL}{path}", headers=headers, **kwargs)
    except httpx.HTTPError as error:
        raise StravaUnavailable(f"Strava is not reachable: {error}") from error
    if response.status_code == 401:
        disconnect(db)
        raise NotConnected("Strava access was revoked — connect it again in Settings.")
    if response.status_code == 404:
        raise NotFound(f"Not found on Strava: {path}")
    if response.status_code >= 500:
        raise StravaUnavailable(f"Strava error {response.status_code}, try again later.")
    if response.status_code >= 400:
        raise StravaError(f"Strava error {response.status_code}: {response.text[:300]}")
    return response.json()
