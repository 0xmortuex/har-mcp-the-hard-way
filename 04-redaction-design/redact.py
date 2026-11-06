"""Module 04: masking secrets.

The design, in order of importance:

1. Mask by NAME. A header, cookie, query parameter or JSON key called authorization,
   cookie, token, password, api_key, ... gets its value replaced, whatever the value is.
2. Mask by SHAPE. A JWT is a secret even in a header called X-Custom.
3. Mask by CONTEXT in free text: `password=hunter2` inside a body we cannot parse.

Masked values become  <redacted:N>  where N is the length. Enough to know a value existed
and roughly what kind (36 chars is a UUID, 900 is a JWT); never the value.

Two properties we test: nothing planted survives, and masking twice changes nothing
(idempotence), so redacting an already-redacted file is safe.
"""

from __future__ import annotations

import json
import re
from typing import Any

NAMES = re.compile(
    r"token|secret|passw(?:or)?d|pwd|api[-_]?key|apikey|auth(?!or(?!iz))|session|csrf|xsrf|credential|signature|jwt|cookie",
    re.I,
)
EXACT = {"key", "sig", "code", "sid", "pass"}
SHAPES = re.compile(r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]*|\bgh[pousr]_[A-Za-z0-9]{16,}|\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")
NAME_VALUE = re.compile(r"(?P<k>[\"']?[A-Za-z0-9_.-]*(?:" + NAMES.pattern + r")[A-Za-z0-9_.-]*[\"']?\s*[:=]\s*)(?P<q>[\"']?)(?!<redacted)(?P<v>[^\"'&\s,;}\]<]+)", re.I)
ALREADY = re.compile(r"<redacted:\d+>")


def mask(value: str) -> str:
    return value if ALREADY.fullmatch(value) else f"<redacted:{len(value)}>"


def sensitive(name: str) -> bool:
    if name.startswith(":"):           # HTTP/2 pseudo headers such as :authority are not secrets
        return False
    low = name.strip().lower()
    if low.startswith("access-control-"):   # CORS: access-control-allow-credentials: true
        return False
    return low in EXACT or NAMES.search(low) is not None


def scrub_text(text: str) -> str:
    text = SHAPES.sub(lambda m: mask(m.group(0)), text)
    return NAME_VALUE.sub(lambda m: m.group("k") + m.group("q") + mask(m.group("v")), text)


def mask_pairs(text: str) -> str:
    """a=1&token=x&b=2  ->  a=1&token=<redacted:1>&b=2"""
    out = []
    for part in text.split("&"):
        name, eq, value = part.partition("=")
        out.append(f"{name}={mask(value)}" if eq and value and sensitive(name) else scrub_text(part))
    return "&".join(out)


def mask_url(url: str) -> str:
    base, hash_, fragment = url.partition("#")
    path, q, query = base.partition("?")
    path = re.sub(r"^([A-Za-z][A-Za-z0-9+.-]*://)([^/?#@]*)@", lambda m: f"{m.group(1)}{mask(m.group(2))}@", path)
    out = scrub_text(path)
    if q:
        out += "?" + mask_pairs(query)
    if hash_:
        out += "#" + (mask_pairs(fragment) if "=" in fragment else scrub_text(fragment))   # OAuth: #access_token=...
    return out


def mask_header(name: str, value: str) -> str:
    low = name.lower()
    if low == "cookie":
        return "; ".join(f"{k.strip()}={mask(v.strip())}" if eq else mask(k) for k, eq, v in (p.partition("=") for p in value.split(";")))
    if low == "set-cookie":
        first, semi, attrs = value.partition(";")
        k, eq, v = first.partition("=")
        return (f"{k}={mask(v)}" if eq else mask(first)) + (";" + attrs if semi else "")
    if low in ("authorization", "proxy-authorization"):
        scheme, space, rest = value.partition(" ")
        return f"{scheme} {mask(rest)}" if space else mask(value)     # keep "Bearer": it is not secret
    if sensitive(name):
        return mask(value)
    return scrub_text(value)


def mask_leaves(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: mask_leaves(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [mask_leaves(v) for v in obj]
    return obj if obj is None or isinstance(obj, bool) else mask(str(obj))


def redact_body(text: str, mime: str = "") -> str:
    if "json" in mime or text.lstrip()[:1] in "{[":
        try:
            return json.dumps(redact(json.loads(text)), separators=(",", ":"))
        except ValueError:
            pass                                      # not JSON after all: treat as text
    if "x-www-form-urlencoded" in mime:
        return mask_pairs(text)
    return scrub_text(text)


def redact(obj: Any, parent: str = "") -> Any:
    """A masked copy of any JSON value: one function that handles a whole HAR entry."""
    if isinstance(obj, str):
        return scrub_text(obj)
    if isinstance(obj, list):
        return [redact(v, parent) for v in obj]
    if not isinstance(obj, dict):
        return obj
    name, value = obj.get("name"), obj.get("value")
    if isinstance(name, str) and isinstance(value, str):
        # {"name": "Authorization", "value": "..."} - a header, query parameter or cookie
        always = parent == "cookies"
        masked = mask(value) if always and value else mask_header(name, value) if value else value
        return {k: (masked if k == "value" else redact(v, k)) for k, v in obj.items()}
    out = {}
    for key, val in obj.items():
        if key == "text" and isinstance(val, str) and parent in ("postData", "content"):
            out[key] = redact_body(val, str(obj.get("mimeType", "")))
        elif key.lower() in ("url", "redirecturl") and isinstance(val, str):
            out[key] = mask_url(val)
        elif sensitive(key) and key.lower() != "cookies" and val not in ("", None):
            out[key] = mask_leaves(val)
        else:
            out[key] = redact(val, key)
    return out
