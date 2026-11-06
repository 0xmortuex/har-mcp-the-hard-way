"""Module 01: turn a raw HAR entry (a big nested dict) into a small flat record."""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from typing import Any

_ISO = re.compile(r"^(\d{4})-(\d\d)-(\d\d)[T ](\d\d):(\d\d):(\d\d)(?:\.(\d+))?\s*(Z|[+-]\d\d:?\d\d)?$", re.I)


def parse_iso_ms(text: Any) -> float | None:
    """ISO 8601 to epoch milliseconds, or None if it is not a timestamp.

    Python 3.10's datetime.fromisoformat rejects the trailing 'Z' and fractions that are
    not 3 or 6 digits, and real HAR files contain both, so we parse by hand. A timestamp
    with no zone is read as UTC."""
    if not isinstance(text, str):
        return None
    m = _ISO.match(text.strip())
    if not m:
        return None
    y, mo, d, h, mi, s = (int(m.group(i)) for i in range(1, 7))
    ms = calendar.timegm((y, mo, d, h, mi, s, 0, 0, 0)) * 1000.0
    if m.group(7):
        ms += int(m.group(7)[:6].ljust(6, "0")) / 1000.0
    tz = m.group(8)
    if tz and tz.upper() != "Z":
        digits = tz[1:].replace(":", "")
        minutes = int(digits[:2]) * 60 + int(digits[2:4])
        ms -= (-1 if tz[0] == "-" else 1) * minutes * 60_000.0
    return ms


def number(value: Any, default: float = -1.0) -> float:
    """HAR numbers are sometimes missing, null or strings. Anything else becomes `default`."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return default


def status_code(value: Any) -> int:
    """Postman writes the status as a string ("200"); some tools omit it."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


@dataclass
class Entry:
    index: int
    start: float | None          # epoch milliseconds, None if the entry has no usable timestamp
    method: str
    url: str
    status: int
    mime: str
    time: float                  # the HAR's own total for the request, -1 if absent
    timings: dict[str, Any]      # the raw blocked/dns/connect/ssl/send/wait/receive numbers
    initiator_url: str           # what triggered this request (Chrome's _initiator), "" if unknown
    redirect_url: str
    transfer: float
    content_size: float


def parse_entry(index: int, raw: Any) -> Entry:
    if not isinstance(raw, dict):
        raise ValueError(f"entry {index} is not a JSON object (found {type(raw).__name__})")
    req = raw.get("request") or {}
    resp = raw.get("response") or {}
    content = resp.get("content") or {}
    init = raw.get("_initiator") or {}
    transfer = number(resp.get("_transferSize"))
    if transfer < 0:  # not Chrome: headers + body, with -1 meaning unknown
        transfer = max(number(resp.get("headersSize")), 0) + max(number(resp.get("bodySize")), 0)
    return Entry(
        index=index,
        start=parse_iso_ms(raw.get("startedDateTime")),
        method=str(req.get("method", "GET")).upper(),
        url=str(req.get("url", "")),
        status=status_code(resp.get("status")),
        mime=str(content.get("mimeType", "")).split(";")[0].strip().lower(),
        time=number(raw.get("time")),
        timings=raw.get("timings") or {},
        initiator_url=str(init.get("url", "")),
        redirect_url=str(resp.get("redirectURL", "")),
        transfer=transfer,
        content_size=max(number(content.get("size")), 0),
    )
