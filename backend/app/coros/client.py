"""COROS MCP access. The protocol lets sync logic be tested with a fake client."""

import base64
from datetime import date
from typing import Protocol

import anyio
import httpx2
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client


class CorosError(Exception):
    """A COROS tool call failed or returned something unusable."""


class CorosClient(Protocol):
    """Calls the sync needs; each returns the tool's raw text (FIT: bytes)."""

    def list_records(self, start: date, end: date) -> str: ...
    def download_fit(self, label_id: str, sport_type: int) -> bytes: ...
    def activity_detail(self, label_id: str, sport_type: int) -> str: ...
    def recovery(self) -> str: ...
    def training_load(self, days: int) -> str: ...


def _text(result) -> str:
    """Join text items of a tool result; raise on tool errors."""
    text = "\n".join(c.text for c in result.content if hasattr(c, "text"))
    if result.is_error:
        raise CorosError(text or "COROS tool error")
    return text


def _blob(result) -> bytes:
    """First embedded binary resource (the FIT file) of a tool result."""
    for item in result.content:
        blob = getattr(getattr(item, "resource", None), "blob", None)
        if blob:
            return base64.b64decode(blob)
    raise CorosError(_text(result) or "No FIT file in COROS response")


class McpCorosClient:
    """Synchronous wrapper: one short MCP session per call (sync runs in a worker)."""

    def __init__(self, server_url: str, token: str):
        """Remember endpoint and bearer token."""
        self.server_url, self.token = server_url, token

    async def _call(self, tool: str, args: dict):
        """Open a session, call one tool, close."""
        headers = {"Authorization": f"Bearer {self.token}"}
        async with httpx2.AsyncClient(headers=headers, timeout=120) as http:
            async with streamable_http_client(self.server_url, http_client=http) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()
                    return await session.call_tool(tool, args)

    def _run(self, tool: str, args: dict):
        """Run one tool call from synchronous code."""
        return anyio.run(self._call, tool, args)

    def list_records(self, start: date, end: date) -> str:
        """querySportRecords for a date window."""
        args = {
            "startDate": start.strftime("%Y%m%d"),
            "endDate": end.strftime("%Y%m%d"),
            "limit": 100,
        }
        return _text(self._run("querySportRecords", args))

    def download_fit(self, label_id: str, sport_type: int) -> bytes:
        """Original FIT of one activity (by labelId — date-range calls are refused)."""
        args = {"labelId": label_id, "sportType": sport_type}
        return _blob(self._run("downloadActivityFitFiles", args))

    def activity_detail(self, label_id: str, sport_type: int) -> str:
        """getActivityDetail text (training load, TE)."""
        return _text(self._run("getActivityDetail", {"labelId": label_id, "sportType": sport_type}))

    def recovery(self) -> str:
        """queryRecoveryStatus text."""
        return _text(self._run("queryRecoveryStatus", {}))

    def training_load(self, days: int) -> str:
        """queryTrainingLoadAssessment text."""
        return _text(self._run("queryTrainingLoadAssessment", {"days": days}))
