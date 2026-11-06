"""Module 02: streaming JSON.

1. Proves the streaming reader agrees with json.load even when the chunk size is 1 byte
   (every boundary lands in the middle of something).
2. Builds a ~20 MB HAR and measures peak Python memory for json.load versus the stream.
3. Shows the errors: truncated file, not a HAR.
"""

import io
import json
import os
import sys
import tempfile
import time
import tracemalloc

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import modpath  # noqa: E402

modpath.use("01-har-anatomy", "02-streaming-json")
import samples  # noqa: E402
from entry import parse_entry  # noqa: E402
from stream import StreamError, walk  # noqa: E402

tmp = tempfile.mkdtemp()

# --- 1. correctness at hostile chunk sizes -----------------------------------------------------
doc = samples.chrome_like()
doc["log"]["entries"][0]["response"]["content"]["text"] = "café 中文 \U0001f600 " * 50  # multi-byte characters
data = json.dumps(doc, ensure_ascii=False).encode("utf-8")
for chunk in (1, 2, 3, 7, 64, 4096, 1 << 20):
    events = list(walk(io.BytesIO(data), chunk))
    entries = [v for kind, _, v in events if kind == "entry"]
    assert entries == doc["log"]["entries"], f"chunk={chunk}"
    assert ("log", "version", "1.2") in events
print("chunk sizes 1..1MiB all agree with json.load")

# a BOM (Postman, some Windows tools) is ignored
assert len([e for e in walk(io.BytesIO(b"\xef\xbb\xbf" + data), 5) if e[0] == "entry"]) == 6

# --- 2. memory: json.load vs the stream ----------------------------------------------------------
big = os.path.join(tmp, "big.har")
n = samples.write_big(big, 20)
size_mb = os.path.getsize(big) / 2**20
print(f"generated {n} entries, {size_mb:.0f} MB")


def peak_of(fn):
    tracemalloc.start()
    t = time.perf_counter()
    result = fn()
    elapsed = time.perf_counter() - t
    peak = tracemalloc.get_traced_memory()[1] / 2**20
    tracemalloc.stop()
    return result, peak, elapsed


def load_all():
    with open(big, encoding="utf-8") as fh:
        return len(json.load(fh)["log"]["entries"])


def stream_all():
    total_wait = count = 0
    with open(big, "rb") as fh:
        for kind, i, raw in walk(fh):
            if kind == "entry":
                total_wait += parse_entry(i, raw).timings["wait"]  # one entry alive at a time
                count += 1
    return count, total_wait


count_a, peak_a, t_a = peak_of(load_all)
(count_b, total_wait), peak_b, t_b = peak_of(stream_all)
print(f"json.load : peak {peak_a:7.1f} MB  {t_a:5.1f} s")
print(f"stream    : peak {peak_b:7.1f} MB  {t_b:5.1f} s")
assert count_a == count_b == n
assert total_wait == sum(i % 50 + 1 for i in range(n))  # exact, not approximate
assert peak_b < peak_a / 5, "the stream should need a small fraction of json.load's memory"
assert peak_b < 30, "and it should not grow with the file"


# --- 3. errors say what is wrong ---------------------------------------------------------------------
def fails(payload: bytes, text: str) -> None:
    try:
        list(walk(io.BytesIO(payload)))
    except StreamError as e:
        assert text in str(e), str(e)
    else:
        raise AssertionError("expected a StreamError")


fails(b'{"log": {"entries": [{"a": 1}, {"b": ', "invalid JSON")  # truncated download
fails(b'{"hello": 1}', "no top-level 'log'")
fails(b"[1, 2]", "top level must be a JSON object")
fails(b"", "top level must be a JSON object")
print("module 02 ok")
