"""Module 01: what is inside a HAR file?

Loads the sample with plain json.load (fine for a small file; module 02 explains why it is
not fine for a big one), prints the anatomy, and checks the facts the rest of the course
relies on.
"""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import modpath  # noqa: E402

modpath.use("01-har-anatomy")
import samples  # noqa: E402
from entry import parse_entry, parse_iso_ms  # noqa: E402

path = samples.write(os.path.join(tempfile.mkdtemp(), "sample.har"), samples.chrome_like())
with open(path, encoding="utf-8") as fh:
    doc = json.load(fh)

log = doc["log"]
print("top level keys :", list(doc))
print("log keys       :", list(log))
print("entries        :", len(log["entries"]))
raw = log["entries"][0]
print("entry keys     :", list(raw))
print("request keys   :", list(raw["request"]))
print("response keys  :", list(raw["response"]))
print("timings        :", raw["timings"])

entries = [parse_entry(i, e) for i, e in enumerate(log["entries"])]
for e in entries:
    print(f"  #{e.index} {e.method:<4} {e.status} time={e.time:>5.0f} ms  {e.url}")

# --- the facts the rest of the course builds on ---------------------------------------------
assert list(doc) == ["log"]
assert len(entries) == 6
assert entries[0].method == "GET" and entries[4].method == "POST" and entries[4].status == 302

# 1. `time` is the entry's total. For entry 0: 5 + 20 + 40 + 1 + 200 + 50 = 316 (module 03 explains
#    why the 30 ms of `ssl` is not added: it is already inside `connect`).
assert entries[0].time == 316
assert entries[0].timings["ssl"] == 30 and entries[0].timings["connect"] == 40

# 2. -1 means "this phase does not apply", not "negative time".
assert entries[1].timings["dns"] == -1 and entries[1].timings["ssl"] == -1

# 3. Timestamps are ISO 8601 and get converted once, here, to epoch milliseconds.
assert parse_iso_ms("2024-05-01T12:00:00.000Z") == 1714564800000.0
assert entries[1].start - entries[0].start == 330
assert parse_iso_ms("2024-05-01T14:00:00+02:00") == parse_iso_ms("2024-05-01T12:00:00Z")   # offsets
assert parse_iso_ms("2024-05-01T12:00:00.5Z") == 1714564800500.0                           # odd fraction length
assert parse_iso_ms("not a time") is None and parse_iso_ms(None) is None

# 4. Chrome adds `_initiator` (who triggered the request); other tools do not, so it is optional.
assert entries[1].initiator_url == "https://example.com/"
assert entries[0].initiator_url == ""

# 5. A redirect is just a 3xx entry with a redirectURL, followed by another entry.
assert entries[4].redirect_url == "/home"

# 6. Missing or odd fields must not crash the parser.
bare = parse_entry(0, {"request": {"url": "http://x/"}, "response": {"status": "404"}})
assert bare.status == 404 and bare.time == -1 and bare.start is None and bare.timings == {}

print("module 01 ok")
