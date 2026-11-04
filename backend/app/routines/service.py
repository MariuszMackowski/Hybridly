"""YouTube video library and home routines."""

import re
from urllib.parse import parse_qs, urlparse

import httpx

_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
OEMBED = "https://www.youtube.com/oembed"
FALLBACK_TITLE = "YouTube video"


def _http() -> httpx.Client:
    """HTTP client factory (patched in tests)."""
    return httpx.Client(timeout=5)


def youtube_id(url: str) -> str | None:
    """Video id from watch / youtu.be / shorts / embed URLs."""
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower().removeprefix("www.").removeprefix("m.")
    candidate = None
    if host == "youtu.be":
        candidate = parsed.path.strip("/").split("/")[0]
    elif host.endswith("youtube.com"):
        if parsed.path == "/watch":
            candidate = parse_qs(parsed.query).get("v", [None])[0]
        else:
            parts = parsed.path.strip("/").split("/")
            if len(parts) >= 2 and parts[0] in ("shorts", "embed", "live", "v"):
                candidate = parts[1]
    return candidate if candidate and _ID.match(candidate) else None


def fetch_oembed(url: str) -> tuple[str, str | None]:
    """(title, thumbnail) from YouTube oEmbed; a generic title when unavailable."""
    try:
        with _http() as http:
            response = http.get(OEMBED, params={"url": url, "format": "json"})
        if response.status_code == 200:
            data = response.json()
            return data.get("title") or FALLBACK_TITLE, data.get("thumbnail_url")
    except (httpx.HTTPError, ValueError):
        pass
    return FALLBACK_TITLE, None
