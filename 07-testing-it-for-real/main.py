"""Module 07: testing it for real.

Unit tests of pure functions are necessary and not enough. A HAR tool fails in four ways
that need dedicated tests:

  1. BOUNDARIES   the streaming reader meets a chunk boundary in the middle of a token.
                  -> fuzz it: random chunk sizes against json.load, many seeds.
  2. LEAKS        a secret sneaks into some output you did not think about.
                  -> plant known fakes, call EVERY tool, grep ALL output.
  3. SCALE        it works on 6 entries and dies on 60,000.
                  -> generate a big file and assert on memory and time, not just results.
  4. HOSTILE FILES  empty, truncated, wrong shape, odd types.
                  -> every one must produce an actionable error, never a traceback.

Usage: python main.py          (30 MB big-file test)
       python main.py --big    (100 MB, what CI's large-file job does)
"""

import io
import json
import os
import random
import sys
import tempfile
import time
import tracemalloc

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import modpath  # noqa: E402

modpath.use("01-har-anatomy", "02-streaming-json", "03-timing-math", "04-redaction-design", "05-waterfall-rendering", "06-mcp-wrapper")
import samples  # noqa: E402
import server  # noqa: E402  (module 06: importing it registers the tools but does not start it)
from stream import StreamError, walk  # noqa: E402

tmp = tempfile.mkdtemp()
server.ALLOWED[:] = [os.path.realpath(tmp)]
EXPECTED = (StreamError, ValueError, OSError)
BIG_MB = 100 if "--big" in sys.argv else 30

# --- 1. boundaries: random chunk sizes, many seeds -------------------------------------------------------
doc = samples.chrome_like()
doc["log"]["entries"][0]["response"]["content"]["text"] = "naïve 中文 \U0001f600 \"quoted\" \\ back\\slash \n newline " * 40
doc["log"]["entries"].append({"n": [1, -2.5e10, 3.14, 12345678901234567890, True, None], "empty": {}, "list": []})
for indent in (None, 2):
    data = json.dumps(doc, indent=indent, ensure_ascii=False).encode("utf-8")
    for seed in range(200):
        rng = random.Random(seed)
        chunk = rng.choice([1, 2, 3, 5, 8, 13, 21, 100, 1000])
        got = [v for kind, _, v in walk(io.BytesIO(data), chunk) if kind == "entry"]
        assert got == doc["log"]["entries"], f"seed={seed} chunk={chunk} indent={indent}"
print("1. boundaries: 400 random chunkings agree with json.load")

# --- 2. leaks: plant, call everything, grep everything ----------------------------------------------------------
har = samples.write(os.path.join(tmp, "site.har"), samples.chrome_like())
outputs = {
    "overview": server.har_overview(har),
    "slowest": server.slowest_requests(har, 6),
    "waterfall": server.waterfall(har),
}
out_path = os.path.join(tmp, "clean.har")
server.redact_har(har, out_path)
outputs["redacted file"] = open(out_path, encoding="utf-8").read()
for name, text in outputs.items():
    for secret in samples.SECRETS:
        assert secret not in text, f"LEAK of {secret} in {name}"
# and the sweep itself is not vacuous: the secrets are in the input
raw = open(har, encoding="utf-8").read()
assert all(s in raw for s in samples.SECRETS)
print(f"2. leaks: {len(samples.SECRETS)} planted secrets, {len(outputs)} outputs, none leaked")

# --- 3. scale ------------------------------------------------------------------------------------------------
big = os.path.join(tmp, "big.har")
n = samples.write_big(big, BIG_MB)
size_mb = os.path.getsize(big) / 2**20
tracemalloc.start()
t = time.perf_counter()
text = server.slowest_requests(big, 3)
elapsed = time.perf_counter() - t
peak = tracemalloc.get_traced_memory()[1] / 2**20
tracemalloc.stop()
print(f"3. scale: {n} entries, {size_mb:.0f} MB; slowest_requests took {elapsed:.1f} s, peak Python memory {peak:.1f} MB")
# entry i has wait = i % 50 + 1, so the max is wait 50 + send 1 + receive 2 = 53 ms, first reached at i = 49
assert text.splitlines()[0].startswith("#49 GET 200 53 ms"), text
assert peak < 40, "memory must not grow with the file"

# --- 4. hostile files: every one is a clean ToolError ---------------------------------------------------------
hostile = {
    "empty.har": "",
    "truncated.har": '{"log": {"entries": [{"request": {"url": "http://x/"}}, {"requ',
    "not-json.har": "<html>this is a login page, not a HAR</html>",
    "wrong-shape.har": '{"hello": "world"}',
    "log-not-object.har": '{"log": []}',
    "entry-not-object.har": '{"log": {"entries": [42]}}',
}
for name, content in hostile.items():
    path = os.path.join(tmp, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    try:
        server.har_overview(path)    # the raw function: tool() registered a wrapper, it did not replace it
    except EXPECTED as e:            # exactly what the wrapper turns into a ToolError for the client
        assert str(e) and "Traceback" not in str(e)
        print(f"   {name:<22} -> {type(e).__name__}: {str(e)[:60]}")
    else:
        raise AssertionError(f"{name}: should have been rejected")
    # (an AttributeError/TypeError/KeyError here would NOT be caught: it is a bug, and the test fails)
print("4. hostile files: all rejected with a message")
print("module 07 ok")
