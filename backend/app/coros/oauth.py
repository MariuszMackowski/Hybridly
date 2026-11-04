"""OAuth 2.1 (dynamic client registration + PKCE) against the COROS MCP authorization server.

The flow is split across two HTTP requests of the app (start → user logs in on the
phone/laptop → finish), which is why it is implemented here instead of via the MCP SDK.
"""

import base64
import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from sqlalchemy.orm import Session

from app.coros.models import CorosAccount

SCOPE = "openid mcp.tools offline_access"
REFRESH_MARGIN = timedelta(minutes=5)


class OAuthError(Exception):
    """The authorization or token exchange failed."""


class NeedsReconnect(OAuthError):
    """Stored tokens can no longer be refreshed; the user must connect again."""


@dataclass(frozen=True)
class AuthServer:
    """Endpoints of the COROS authorization server."""

    authorize: str
    token: str
    register: str


def _http() -> httpx.Client:
    """HTTP client factory (patched in tests)."""
    return httpx.Client(timeout=30)


def _origin(server_url: str) -> str:
    """Scheme + host of the MCP server URL."""
    parsed = urlparse(server_url)
    return f"{parsed.scheme}://{parsed.netloc}"


def discover(server_url: str) -> AuthServer:
    """Read authorization server metadata (RFC 8414)."""
    with _http() as http:
        response = http.get(f"{_origin(server_url)}/.well-known/oauth-authorization-server")
    response.raise_for_status()
    meta = response.json()
    return AuthServer(
        meta["authorization_endpoint"], meta["token_endpoint"], meta["registration_endpoint"]
    )


def get_account(db: Session, server_url: str | None = None) -> CorosAccount:
    """The single COROS account row, created on first use."""
    account = db.get(CorosAccount, 1)
    if account is None:
        account = CorosAccount(id=1, server_url=server_url or "", status="disconnected")
        db.add(account)
        db.flush()
    if server_url and account.server_url != server_url:
        account.server_url, account.client_id = server_url, None
    return account


def _register(server: AuthServer, redirect_uri: str) -> str:
    """Dynamic client registration of a public client; returns client_id."""
    with _http() as http:
        response = http.post(
            server.register,
            json={
                "client_name": "Hybridly",
                "redirect_uris": [redirect_uri],
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "token_endpoint_auth_method": "none",
                "scope": SCOPE,
            },
        )
    if response.status_code >= 400:
        raise OAuthError(f"Client registration failed: {response.status_code} {response.text}")
    return response.json()["client_id"]


def _challenge(verifier: str) -> str:
    """PKCE S256 code challenge."""
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def start_connect(db: Session, server_url: str, redirect_uri: str) -> str:
    """Prepare PKCE + state (registering a client if needed) and return the authorize URL."""
    account = get_account(db, server_url)
    server = discover(server_url)
    if not account.client_id or account.redirect_uri != redirect_uri:
        account.client_id = _register(server, redirect_uri)
        account.redirect_uri = redirect_uri
    account.pending_state = secrets.token_urlsafe(24)
    account.pending_verifier = secrets.token_urlsafe(48)
    db.commit()
    params = {
        "response_type": "code",
        "client_id": account.client_id,
        "redirect_uri": redirect_uri,
        "state": account.pending_state,
        "code_challenge": _challenge(account.pending_verifier),
        "code_challenge_method": "S256",
        "resource": server_url,
        "scope": SCOPE,
        "prompt": "consent",
    }
    return f"{server.authorize}?{urlencode(params)}"


def _store_tokens(account: CorosAccount, payload: dict) -> None:
    """Save a token response on the account."""
    account.access_token = payload["access_token"]
    account.refresh_token = payload.get("refresh_token", account.refresh_token)
    account.expires_at = datetime.now(UTC) + timedelta(seconds=int(payload.get("expires_in", 3600)))
    account.status = "connected"


def _token_request(account: CorosAccount, form: dict) -> httpx.Response:
    """POST to the token endpoint as a public client."""
    server = discover(account.server_url)
    with _http() as http:
        return http.post(server.token, data={**form, "client_id": account.client_id})


def finish_connect(db: Session, callback_url: str) -> None:
    """Exchange the code from the redirect URL (callback or pasted by the user) for tokens."""
    account = get_account(db)
    query = {k: v[0] for k, v in parse_qs(urlparse(callback_url.strip()).query).items()}
    if "error" in query:
        raise OAuthError(f"COROS refused access: {query['error']}")
    if not account.pending_state or query.get("state") != account.pending_state:
        raise OAuthError("Login link expired or does not match — start the connection again.")
    if "code" not in query:
        raise OAuthError("No authorization code in the URL.")
    response = _token_request(
        account,
        {
            "grant_type": "authorization_code",
            "code": query["code"],
            "redirect_uri": account.redirect_uri,
            "code_verifier": account.pending_verifier,
        },
    )
    if response.status_code >= 400:
        raise OAuthError(f"Token exchange failed: {response.status_code} {response.text}")
    _store_tokens(account, response.json())
    account.pending_state = account.pending_verifier = None
    db.commit()


def get_access_token(db: Session) -> str:
    """A valid access token, refreshed when close to expiry."""
    account = get_account(db)
    if account.status != "connected" or not account.access_token:
        raise NeedsReconnect("COROS is not connected.")
    if account.expires_at and account.expires_at - datetime.now(UTC) > REFRESH_MARGIN:
        return account.access_token
    response = _token_request(
        account, {"grant_type": "refresh_token", "refresh_token": account.refresh_token}
    )
    if response.status_code >= 400:
        account.status = "needs_reconnect"
        db.commit()
        raise NeedsReconnect(f"Token refresh failed: {response.status_code}")
    _store_tokens(account, response.json())
    db.commit()
    return account.access_token
