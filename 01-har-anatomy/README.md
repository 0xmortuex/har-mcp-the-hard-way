# Module 01: HAR Anatomy

## The concept

HAR ("HTTP Archive") is what browsers write when you do *Network tab → Save all as HAR*. It is
plain JSON with one fixed skeleton:

```
{ "log": {
    "version": "1.2",
    "creator": {...},          which tool wrote it
    "pages":   [ {...} ],      page loads, with onContentLoad / onLoad timings
    "entries": [               ONE PER HTTP REQUEST - this is 99.9% of the file
      { "startedDateTime": "2024-05-01T12:00:00.000Z",
        "time": 316,                                  total ms
        "request":  { method, url, headers[], queryString[], cookies[], postData{} },
        "response": { status, headers[], content{ size, mimeType, text, encoding }, redirectURL },
        "timings":  { blocked, dns, connect, ssl, send, wait, receive },
        "cache": {}, "pageref": "page_1",
        "_initiator": {...}   <- extensions start with "_": Chrome adds several
      }, ...
```

Everything an agent could want is in there. The trouble is that real files vary: Chrome
adds `_initiator`, `_priority`, `_transferSize`; Firefox fills unknown timings with `-1`;
Postman writes the status as the string `"200"` and prepends a UTF-8 BOM; mitmproxy leaves
out `time` and some timings. The first job of the server is to absorb that variety **once**,
in one function, so every tool downstream deals with one clean record.

That function is `parse_entry` in `entry.py`. It turns the nested dict into a flat
`Entry`: method, url, status, mime, start time in epoch milliseconds, the raw timings, the
initiator, the redirect target and sizes.

## The code

- `entry.py` — `parse_iso_ms` (a hand-written ISO 8601 parser, because Python 3.10's
  `fromisoformat` rejects the trailing `Z` that HAR files use), `number` (anything that is
  not a real number becomes the default), `status_code`, `parse_entry`.
- `main.py` — loads `samples.py`'s six-request capture, prints the structure, and asserts:
  `time` is 316 for the first request, `-1` appears for phases that did not happen,
  timestamps parse across offsets and odd fractions, `_initiator` is optional, and a nearly
  empty entry does not crash the parser.

```bash
python 01-har-anatomy/main.py
```

## Why a flat record

An agent-facing server lives or dies on **what it keeps in memory** and **what it prints**.
Module 02 will stream a 200 MB file one entry at a time; the `Entry` is what we keep from each
one (a few hundred bytes) while the heavy parts (headers, bodies) are thrown away and re-read
only when the agent asks for one specific request.

Next: [Module 02](../02-streaming-json) — reading the file without loading it.
