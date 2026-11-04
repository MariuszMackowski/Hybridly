import pytest

from app.coros import router as coros_router
from app.coros.models import CorosAccount


class FakeLock:
    """In-memory stand-in for the Redis sync lock."""

    def __init__(self, held=False):
        self.held = held

    def is_held(self):
        return self.held


@pytest.fixture
def lock(monkeypatch):
    fake = FakeLock()
    monkeypatch.setattr(coros_router, "sync_lock", lambda: fake)
    return fake


def test_status_disconnected_by_default(client, lock):
    body = client.get("/api/coros/status").json()
    assert body["status"] == "disconnected"
    assert body["syncing"] is False


def test_connect_returns_authorize_url(client, lock, monkeypatch):
    calls = {}

    def fake_start(db, server_url, redirect_uri):
        calls["redirect"] = redirect_uri
        return "https://auth.example/authorize?x=1"

    monkeypatch.setattr(coros_router.oauth, "start_connect", fake_start)
    monkeypatch.setattr(coros_router, "_public_url", lambda: "https://home.example.ts.net")
    body = client.post("/api/coros/connect").json()
    assert body["authorize_url"].startswith("https://auth.example/")
    assert calls["redirect"] == "https://home.example.ts.net/api/coros/callback"


def test_complete_with_pasted_url_connects(client, db_session, lock, monkeypatch):
    def fake_finish(db, url):
        db.add(CorosAccount(id=1, server_url="x", status="connected"))
        db.flush()

    enqueued = []
    monkeypatch.setattr(coros_router.oauth, "finish_connect", fake_finish)
    monkeypatch.setattr(coros_router, "enqueue_sync", lambda: enqueued.append(1))
    response = client.post(
        "/api/coros/complete", json={"url": "http://localhost:8765/callback?code=a"}
    )
    assert response.status_code == 200
    assert client.get("/api/coros/status").json()["status"] == "connected"
    assert enqueued == [1]


def test_complete_with_bad_url_returns_400(client, lock, monkeypatch):
    def fake_finish(db, url):
        raise coros_router.oauth.OAuthError("Login link expired")

    monkeypatch.setattr(coros_router.oauth, "finish_connect", fake_finish)
    response = client.post("/api/coros/complete", json={"url": "http://x/?code=a"})
    assert response.status_code == 400
    assert "expired" in response.json()["detail"]


def test_sync_endpoint_enqueues(client, db_session, lock, monkeypatch):
    db_session.add(CorosAccount(id=1, server_url="x", status="connected"))
    db_session.flush()
    enqueued = []
    monkeypatch.setattr(coros_router, "enqueue_sync", lambda: enqueued.append(1))
    assert client.post("/api/coros/sync").status_code == 202
    assert enqueued == [1]


def test_sync_conflict_when_locked(client, db_session, lock, monkeypatch):
    db_session.add(CorosAccount(id=1, server_url="x", status="connected"))
    db_session.flush()
    lock.held = True
    monkeypatch.setattr(coros_router, "enqueue_sync", lambda: None)
    assert client.post("/api/coros/sync").status_code == 409


def test_sync_requires_connection(client, lock):
    assert client.post("/api/coros/sync").status_code == 409
