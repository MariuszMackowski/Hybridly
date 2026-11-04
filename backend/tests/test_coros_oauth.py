import base64
import hashlib
import json
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from app.coros import oauth
from app.coros.models import CorosAccount

SERVER = "https://mcp.example.test/mcp"
ISSUER = "https://mcp.example.test"
REDIRECT = "https://home.example.ts.net/api/coros/callback"


class FakeAS:
    """Minimal OAuth authorization server for httpx.MockTransport."""

    def __init__(self, refresh_ok=True):
        self.registrations = 0
        self.token_requests: list[dict] = []
        self.refresh_ok = refresh_ok

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/.well-known/oauth-authorization-server":
            return httpx.Response(
                200,
                json={
                    "issuer": ISSUER,
                    "authorization_endpoint": f"{ISSUER}/oauth2/authorize",
                    "token_endpoint": f"{ISSUER}/oauth2/token",
                    "registration_endpoint": f"{ISSUER}/connect/register",
                },
            )
        if path == "/connect/register":
            self.registrations += 1
            body = json.loads(request.content)
            return httpx.Response(201, json={"client_id": f"client-{self.registrations}", **body})
        if path == "/oauth2/token":
            form = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
            self.token_requests.append(form)
            if form["grant_type"] == "refresh_token" and not self.refresh_ok:
                return httpx.Response(400, json={"error": "invalid_grant"})
            return httpx.Response(
                200,
                json={
                    "access_token": f"at-{len(self.token_requests)}",
                    "refresh_token": f"rt-{len(self.token_requests)}",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                },
            )
        return httpx.Response(404)


@pytest.fixture
def fake_as(monkeypatch):
    server = FakeAS()
    monkeypatch.setattr(oauth, "_http", lambda: httpx.Client(transport=httpx.MockTransport(server)))
    return server


def _query(url):
    return {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}


def test_start_connect_builds_pkce_url_and_registers_once(db_session, fake_as):
    oauth.start_connect(db_session, SERVER, REDIRECT)
    url = oauth.start_connect(db_session, SERVER, REDIRECT)
    q = _query(url)
    verifier = db_session.get(CorosAccount, 1).pending_verifier
    expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
    assert url.startswith(f"{ISSUER}/oauth2/authorize?")
    assert q["code_challenge"] == expected.rstrip(b"=").decode()
    assert q["code_challenge_method"] == "S256"
    assert q["redirect_uri"] == REDIRECT
    assert q["resource"] == SERVER
    assert q["scope"] == "openid mcp.tools offline_access"
    assert fake_as.registrations == 1


def test_finish_connect_rejects_wrong_state(db_session, fake_as):
    oauth.start_connect(db_session, SERVER, REDIRECT)
    with pytest.raises(oauth.OAuthError):
        oauth.finish_connect(db_session, f"{REDIRECT}?code=abc&state=wrong")


def test_finish_connect_stores_tokens(db_session, fake_as):
    state = _query(oauth.start_connect(db_session, SERVER, REDIRECT))["state"]
    oauth.finish_connect(db_session, f"{REDIRECT}?code=abc&state={state}")
    account = db_session.get(CorosAccount, 1)
    assert account.status == "connected"
    assert account.access_token == "at-1"
    assert account.pending_state is None
    assert fake_as.token_requests[0]["code_verifier"]
    assert fake_as.token_requests[0]["redirect_uri"] == REDIRECT


def test_token_refreshed_when_expiring(db_session, fake_as):
    state = _query(oauth.start_connect(db_session, SERVER, REDIRECT))["state"]
    oauth.finish_connect(db_session, f"{REDIRECT}?code=abc&state={state}")
    db_session.get(CorosAccount, 1).expires_at = datetime.now(UTC) + timedelta(minutes=2)
    assert oauth.get_access_token(db_session) == "at-2"
    assert fake_as.token_requests[-1]["grant_type"] == "refresh_token"
    assert db_session.get(CorosAccount, 1).refresh_token == "rt-2"


def test_refresh_failure_marks_needs_reconnect(db_session, fake_as):
    state = _query(oauth.start_connect(db_session, SERVER, REDIRECT))["state"]
    oauth.finish_connect(db_session, f"{REDIRECT}?code=abc&state={state}")
    db_session.get(CorosAccount, 1).expires_at = datetime.now(UTC) - timedelta(minutes=1)
    fake_as.refresh_ok = False
    with pytest.raises(oauth.NeedsReconnect):
        oauth.get_access_token(db_session)
    assert db_session.get(CorosAccount, 1).status == "needs_reconnect"


def test_refresh_server_error_is_transient(db_session, fake_as, monkeypatch):
    state = _query(oauth.start_connect(db_session, SERVER, REDIRECT))["state"]
    oauth.finish_connect(db_session, f"{REDIRECT}?code=abc&state={state}")
    db_session.get(CorosAccount, 1).expires_at = datetime.now(UTC) - timedelta(minutes=1)
    original = fake_as.__call__

    def flaky(request):
        if request.url.path == "/oauth2/token":
            return httpx.Response(503)
        return original(request)

    monkeypatch.setattr(oauth, "_http", lambda: httpx.Client(transport=httpx.MockTransport(flaky)))
    with pytest.raises(oauth.OAuthError) as caught:
        oauth.get_access_token(db_session)
    assert not isinstance(caught.value, oauth.NeedsReconnect)
    assert db_session.get(CorosAccount, 1).status == "connected"


def test_network_error_becomes_oauth_error(db_session, monkeypatch):
    def down(request):
        raise httpx.ConnectError("no route")

    monkeypatch.setattr(oauth, "_http", lambda: httpx.Client(transport=httpx.MockTransport(down)))
    with pytest.raises(oauth.OAuthError):
        oauth.start_connect(db_session, SERVER, REDIRECT)
