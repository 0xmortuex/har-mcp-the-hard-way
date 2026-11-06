"""Module 02: read a HAR one entry at a time, in constant memory.

The file is  {"log": { ..., "entries": [ e0, e1, e2, ... ], ... }}.  We walk that skeleton
by hand (braces, commas, keys) and let json.JSONDecoder.raw_decode, which is C code and
fast, decode ONE value at a time: an entry, then the next entry.

The one subtlety: raw_decode cannot tell "this value is cut off because my buffer ends here"
from "this value is malformed". So a decode failure means "read more" until the file is
exhausted, and only then is it a real error. The read size doubles each retry, so a single
huge entry costs a handful of reads instead of thousands.
"""

from __future__ import annotations

import codecs
import json
import re
from collections.abc import Iterator
from typing import Any, BinaryIO

_WS = re.compile(r"[ \t\r\n]*")


class StreamError(ValueError):
    """The file is not a HAR (or not JSON). The message says which."""


class Reader:
    def __init__(self, fh: BinaryIO, chunk: int = 1 << 20) -> None:
        self.fh = fh
        self.chunk = chunk
        # The decoder keeps state, so a multi-byte character split across two reads is fine.
        # utf-8-sig also swallows the BOM that some Windows tools write.
        self.dec = codecs.getincrementaldecoder("utf-8-sig")()
        self.buf = ""
        self.pos = 0
        self.eof = False
        self.json = json.JSONDecoder()

    def fill(self, want: int = 0) -> None:
        if self.eof:
            return
        data = self.fh.read(max(self.chunk, want))
        text = self.dec.decode(data, final=not data)
        if not data:
            self.eof = True
        self.buf = self.buf[self.pos:] + text      # drop what we already consumed
        self.pos = 0

    def peek(self) -> str:
        """The next non-blank character, '' at the end of the file."""
        while True:
            m = _WS.match(self.buf, self.pos)
            assert m is not None
            self.pos = m.end()
            if self.pos < len(self.buf):
                return self.buf[self.pos]
            if self.eof:
                return ""
            self.fill()

    def next_char(self) -> str:
        c = self.peek()
        if c:
            self.pos += 1
        return c

    def expect(self, ch: str) -> None:
        c = self.next_char()
        if c != ch:
            raise StreamError(f"invalid JSON: expected {ch!r}, found {c or 'end of file'!r}")

    def value(self) -> Any:
        """Decode the one JSON value at the cursor."""
        if not self.peek():
            raise StreamError("invalid JSON: the file ends where a value should be")
        want = 0
        while True:
            try:
                val, end = self.json.raw_decode(self.buf, self.pos)
            except json.JSONDecodeError as e:
                if self.eof:
                    raise StreamError(f"invalid JSON: {e.msg}") from e
                want = max(want * 2, self.chunk)       # cut off? read more and try again
                self.fill(want)
                continue
            # "12" at the very end of the buffer might really be "123": read on to be sure.
            if end == len(self.buf) and not self.eof and self.buf[self.pos] in "-0123456789":
                want = max(want * 2, self.chunk)
                self.fill(want)
                continue
            self.pos = end
            return val


def members(r: Reader) -> Iterator[str]:
    """Yield each key of the object at the cursor; the caller must consume the value."""
    r.expect("{")
    if r.peek() == "}":
        r.pos += 1
        return
    while True:
        key = r.value()
        r.expect(":")
        yield key
        c = r.next_char()
        if c == "}":
            return
        if c != ",":
            raise StreamError(f"invalid JSON: expected ',' or '}}', found {c or 'end of file'!r}")


def elements(r: Reader) -> Iterator[Any]:
    r.expect("[")
    if r.peek() == "]":
        r.pos += 1
        return
    while True:
        yield r.value()
        c = r.next_char()
        if c == "]":
            return
        if c != ",":
            raise StreamError(f"invalid JSON: expected ',' or ']', found {c or 'end of file'!r}")


def walk(fh: BinaryIO, chunk: int = 1 << 20) -> Iterator[tuple[str, Any, Any]]:
    """Yield ("log", name, value) for every member of `log` except `entries`, and
    ("entry", position, dict) for each entry, one at a time."""
    r = Reader(fh, chunk)
    if r.peek() != "{":
        raise StreamError("not a HAR file: the top level must be a JSON object")
    saw_log = False
    for top in members(r):
        if top != "log":
            r.value()
            continue
        saw_log = True
        for key in members(r):
            if key == "entries" and r.peek() == "[":
                for i, entry in enumerate(elements(r)):
                    yield "entry", i, entry
            else:
                yield "log", key, r.value()
    if not saw_log:
        raise StreamError("not a HAR file: there is no top-level 'log' member")
