"""Module 03: timing math, checked against exact numbers."""

import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import modpath  # noqa: E402

modpath.use("01-har-anatomy", "02-streaming-json", "03-timing-math")
import samples  # noqa: E402
from entry import parse_entry  # noqa: E402
from stream import walk  # noqa: E402
from timing import describe, dominant, phases, total  # noqa: E402

data = json.dumps(samples.chrome_like()).encode()
entries = [parse_entry(i, raw) for kind, i, raw in walk(io.BytesIO(data)) if kind == "entry"]

# --- the ssl-inside-connect rule ------------------------------------------------------------------
p0 = phases(entries[0].timings)
assert p0 == {"blocked": 5, "dns": 20, "connect": 10, "ssl": 30, "send": 1, "wait": 200, "receive": 50}
assert sum(p0.values()) == 316 == entries[0].time          # the phases add up to `time` exactly

# --- -1 is zero ------------------------------------------------------------------------------------
p1 = phases(entries[1].timings)
assert p1["dns"] == p1["connect"] == p1["ssl"] == 0
assert sum(p1.values()) == 503 == entries[1].time

# --- missing keys, strings, nulls: all zero -----------------------------------------------------------
assert phases({}) == {k: 0 for k in p0}
assert phases({"wait": "12", "receive": None, "send": True})["wait"] == 0

# --- total(): trust `time`, else sum --------------------------------------------------------------------
assert total(99.5, {"wait": 10}) == 99.5                    # declared time wins even if it differs
assert total(-1, {"connect": 50, "ssl": 30, "wait": 10}) == 60   # 20 TCP + 30 TLS + 10 wait, not 90
assert total(-1, {"connect": 10, "ssl": 30, "wait": 10}) == 50   # ssl > connect: a tool put it outside

# --- dominant phase ------------------------------------------------------------------------------------
name, share = dominant(entries[3].timings)                  # the slow API call
assert name == "wait" and abs(share - 900 / 910) < 1e-9
name, share = dominant(entries[1].timings)                  # app.js: a big download
assert name == "receive" and abs(share - 400 / 503) < 1e-9
assert dominant({}) is None
assert dominant({"dns": 10, "wait": 10})[0] == "dns"        # tie: earlier phase

# --- slowest N ------------------------------------------------------------------------------------------
slowest = sorted(entries, key=lambda e: -total(e.time, e.timings))[:3]
print("slowest requests:")
for e in slowest:
    print(f"  #{e.index} {e.method} {total(e.time, e.timings):g} ms {e.url}")
    print("   ", describe(e.timings))
assert [e.index for e in slowest] == [3, 1, 0]              # 910, 503, 316

assert describe(entries[0].timings).splitlines()[0] == "blocked 5 ms | dns 20 ms | connect 10 ms | tls 30 ms | send 1 ms | wait 200 ms | receive 50 ms"
print("module 03 ok")
