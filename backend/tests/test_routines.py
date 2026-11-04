import httpx
import pytest

from app.routines import service
from app.routines.service import youtube_id


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ?si=abc",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "https://m.youtube.com/watch?feature=share&v=dQw4w9WgXcQ",
    ],
)
def test_youtube_id_variants(url):
    assert youtube_id(url) == "dQw4w9WgXcQ"


def test_youtube_id_not_youtube():
    assert youtube_id("https://example.com/video") is None


def _oembed(handler):
    return lambda: httpx.Client(transport=httpx.MockTransport(handler))


def test_add_video_fetches_title(client, monkeypatch):
    monkeypatch.setattr(
        service,
        "_http",
        _oembed(
            lambda r: httpx.Response(
                200, json={"title": "Core 15 min", "thumbnail_url": "https://i.ytimg.com/x.jpg"}
            )
        ),
    )
    body = client.post("/api/videos", json={"url": "https://youtu.be/dQw4w9WgXcQ"}).json()
    assert body["title"] == "Core 15 min"
    assert body["youtube_id"] == "dQw4w9WgXcQ"


def test_add_video_when_oembed_fails(client, monkeypatch):
    monkeypatch.setattr(service, "_http", _oembed(lambda r: httpx.Response(401)))
    body = client.post("/api/videos", json={"url": "https://youtu.be/dQw4w9WgXcQ"}).json()
    assert body["title"] == "YouTube video"
    assert body["url"] == "https://youtu.be/dQw4w9WgXcQ"


def test_routine_week_and_done_log(client, monkeypatch):
    monkeypatch.setattr(service, "_http", _oembed(lambda r: httpx.Response(500)))
    v1 = client.post("/api/videos", json={"url": "https://youtu.be/aaaaaaaaaaa"}).json()["id"]
    v2 = client.post("/api/videos", json={"url": "https://youtu.be/bbbbbbbbbbb"}).json()["id"]
    routine = client.post("/api/routines", json={"name": "Core", "video_ids": [v2, v1]}).json()
    assert [v["id"] for v in routine["videos"]] == [v2, v1]
    client.put("/api/routines/week", json=[{"weekday": 0, "routine_ids": [routine["id"]]}])
    assert client.get("/api/routines/week").json()[0]["routine_ids"] == [routine["id"]]
    assert client.put(f"/api/routines/{routine['id']}/done/2026-01-05").status_code == 204
    done = client.get("/api/routines/done?day=2026-01-05").json()
    assert done == [routine["id"]]
    client.delete(f"/api/routines/{routine['id']}/done/2026-01-05")
    assert client.get("/api/routines/done?day=2026-01-05").json() == []


def test_duplicate_routine_name_returns_409(client):
    client.post("/api/routines", json={"name": "Core", "video_ids": []})
    assert client.post("/api/routines", json={"name": "Core", "video_ids": []}).status_code == 409
