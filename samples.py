"""Sample HAR data shared by every module: small, realistic, with known numbers and
FAKE secrets planted on purpose so the redaction module has something to find.

Nothing here is a real credential.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qsl

BEARER = "FAKEBEARERTOKEN0123456789abcdef"
COOKIE = "FAKESESSIONCOOKIE123456"
API_KEY = "FAKEAPIKEYINQUERY555"
PASSWORD = "FAKEPASSWORDBODY111"
ACCESS = "FAKEACCESSTOKENRESP222"
JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJmYWtlIn0.FAKEJWTSIGNATURE"
SECRETS = [BEARER, COOKIE, API_KEY, PASSWORD, ACCESS, JWT, "FAKEJWTSIGNATURE"]

DOC = "https://example.com/"


def iso(offset_ms: int) -> str:
    secs, ms = divmod(offset_ms, 1000)
    mins, s = divmod(secs, 60)
    return f"2024-05-01T12:{mins:02d}:{s:02d}.{ms:03d}Z"


def timings(blocked=-1, dns=-1, connect=-1, ssl=-1, send=0, wait=0, receive=0) -> dict[str, float]:
    return {"blocked": blocked, "dns": dns, "connect": connect, "ssl": ssl, "send": send, "wait": wait, "receive": receive}


def entry(offset, method, url, status, tm, *, time=None, mime="text/html", req_headers=None, resp_headers=None,
          body=None, post=None, redirect="", initiator=None, size=1000) -> dict[str, Any]:
    if time is None:
        # HAR rule: ssl is INSIDE connect, so it is not added again.
        time = sum(max(v, 0) for k, v in tm.items() if k != "ssl")
    content: dict[str, Any] = {"size": size, "mimeType": mime}
    if body is not None:
        content["text"] = body
    request: dict[str, Any] = {
        "method": method, "url": url, "httpVersion": "h2", "headers": req_headers or [],
        "queryString": [{"name": k, "value": v} for k, v in parse_qsl(url.split("?", 1)[1])] if "?" in url else [],
        "cookies": [], "headersSize": 100, "bodySize": 0,
    }
    if post:
        request["postData"] = post
    e: dict[str, Any] = {
        "pageref": "page_1", "startedDateTime": iso(offset), "time": time, "request": request,
        "response": {"status": status, "statusText": "OK", "httpVersion": "h2", "headers": resp_headers or [],
                     "cookies": [], "content": content, "redirectURL": redirect, "headersSize": 200, "bodySize": size},
        "cache": {}, "timings": tm,
    }
    if initiator:
        e["_initiator"] = initiator
    return e


def hdr(**kw: str) -> list[dict[str, str]]:
    return [{"name": k.replace("_", "-"), "value": v} for k, v in kw.items()]


def chrome_like() -> dict[str, Any]:
    """Six requests. Entry 0 is 316 ms: 5+20+40+1+200+50 (the 30 ms of TLS is inside connect's 40)."""
    parser = {"type": "parser", "url": DOC}
    script = {"type": "script", "url": "https://example.com/app.js"}
    entries = [
        entry(0, "GET", DOC, 200, timings(5, 20, 40, 30, 1, 200, 50), req_headers=hdr(Authorization=f"Bearer {BEARER}", Cookie=f"sessionid={COOKIE}; theme=dark", X_Custom=JWT)),
        entry(330, "GET", "https://example.com/app.js", 200, timings(2, send=1, wait=100, receive=400), mime="application/javascript", initiator=parser),
        entry(330, "GET", "https://example.com/style.css", 200, timings(1, send=1, wait=60, receive=20), mime="text/css", initiator=parser),
        entry(840, "GET", f"https://example.com/api/data?api_key={API_KEY}&page=2", 200, timings(0, send=1, wait=900, receive=9),
              mime="application/json", initiator=script, body=json.dumps({"access_token": ACCESS, "user": "bob"})),
        entry(1760, "POST", "https://example.com/login", 302, timings(0, send=1, wait=120, receive=19), redirect="/home", initiator=script,
              post={"mimeType": "application/json", "text": json.dumps({"username": "bob", "password": PASSWORD})}),
        entry(1905, "GET", "https://example.com/home", 200, timings(0, send=1, wait=150, receive=30), initiator=script),
    ]
    return {"log": {"version": "1.2", "creator": {"name": "WebInspector", "version": "537.36"},
                    "pages": [{"id": "page_1", "title": "Example", "startedDateTime": iso(0), "pageTimings": {"onContentLoad": 900, "onLoad": 2000}}],
                    "entries": entries}}


def write(path: str, doc: dict[str, Any]) -> str:
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh)
    return path


def write_big(path: str, megabytes: int) -> int:
    """Stream a HAR of about `megabytes` MB to disk without building it in memory.
    Entry i has wait = i % 50 + 1 ms and about 8 KB of body. Returns the entry count."""
    body = "x" * 8000
    target = megabytes * 1024 * 1024
    written = n = 0
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write('{"log":{"version":"1.2","entries":[')
        while written < target:
            e = entry(n % 100_000, "GET", f"https://big.example.com/r/{n}", 200, timings(0, send=1, wait=n % 50 + 1, receive=2),
                      mime="text/plain", body=body, size=len(body))
            chunk = ("," if n else "") + json.dumps(e)
            fh.write(chunk)
            written += len(chunk)
            n += 1
        fh.write("]}}")
    return n
