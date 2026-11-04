"""Parsers for COROS MCP tool results, which are human-readable text (pure).

Everything about an activity itself comes from its FIT file; only identifiers,
COROS-computed load/TE and daily recovery/load are read from text here.
"""

import json
import re
from dataclasses import dataclass
from datetime import date

_HEADER = re.compile(r"^\s*\d+\.\s+(?P<sport>.+?)\s+—\s+(?P<day>\d{4}-\d{2}-\d{2})\s*$", re.M)
_IDS = re.compile(r"LabelId:\s*(?P<label>\d+)\s*\|\s*SportType:\s*(?P<sport_type>\d+)")
_LOCATION = re.compile(r"^\s*Location:\s*(?P<name>.+?)\s*$", re.M)


@dataclass(frozen=True)
class RecordRef:
    """Identifier of one COROS activity from querySportRecords."""

    label_id: str
    sport_type: int
    name: str | None
    day: date


def _text(raw: str) -> str:
    """Tool text is sometimes a JSON-encoded string; decode it when it is."""
    stripped = raw.strip()
    if stripped.startswith('"'):
        try:
            decoded = json.loads(stripped)
            if isinstance(decoded, str):
                return decoded
        except json.JSONDecodeError:
            pass
    return raw


def _number(pattern: str, text: str, cast):
    """First captured number for a label pattern, cast, or None."""
    match = re.search(pattern, text)
    return cast(match.group(1)) if match else None


def parse_sport_records(raw: str) -> tuple[list[RecordRef], int]:
    """Activity refs in listed order plus the count of blocks that could not be parsed."""
    text = _text(raw)
    headers = list(_HEADER.finditer(text))
    refs, skipped = [], 0
    for i, header in enumerate(headers):
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        block = text[header.end() : end]
        ids = _IDS.search(block)
        if not ids:
            skipped += 1
            continue
        location = _LOCATION.search(block)
        refs.append(
            RecordRef(
                label_id=ids["label"],
                sport_type=int(ids["sport_type"]),
                name=location["name"] if location else header["sport"],
                day=date.fromisoformat(header["day"]),
            )
        )
    return refs, skipped


def parse_activity_detail(raw: str) -> dict:
    """COROS Training Load and training effects of one activity (missing keys omitted)."""
    text = _text(raw)
    values = {
        "training_load": _number(r"Training Load:\s*(\d+)", text, int),
        "aerobic_te": _number(r"Aerobic TE:\s*([\d.]+)", text, float),
        "anaerobic_te": _number(r"Anaerobic TE:\s*([\d.]+)", text, float),
    }
    return {k: v for k, v in values.items() if v is not None}


def parse_recovery(raw: str) -> dict:
    """Current recovery percentage, level and hours to full recovery."""
    text = _text(raw)
    level = re.search(r"Level:\s*(.+)", text)
    values = {
        "recovery_pct": _number(r"Recovery:\s*(\d+)%", text, int),
        "level": level.group(1).strip() if level else None,
        "full_recovery_h": _number(r"Estimated Full Recovery:\s*(\d+)\s*h", text, int),
    }
    return {k: v for k, v in values.items() if v is not None}


def parse_training_load(raw: str) -> list[dict]:
    """Daily short/long-term load entries, newest first as returned."""
    text = _text(raw)
    days = []
    for block in re.split(r"\n\s*\n", text):
        day = re.search(r"^\s*(\d{4}-\d{2}-\d{2})\s*$", block, re.M)
        if not day:
            continue
        comment = re.search(r"Comment:\s*(.+)", block)
        days.append(
            {
                "day": day.group(1),
                "comment": comment.group(1).strip() if comment else None,
                "short_term": _number(r"Short-Term Load:\s*(\d+)", block, int),
                "long_term": _number(r"Long-Term Load:\s*(\d+)", block, int),
                "ratio": _number(r"Load Ratio:\s*([\d.]+)", block, float),
            }
        )
    return days
