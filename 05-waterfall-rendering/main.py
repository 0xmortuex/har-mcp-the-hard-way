"""Module 05: waterfall and critical path, with exact checks."""

import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import modpath  # noqa: E402

modpath.use("01-har-anatomy", "02-streaming-json", "03-timing-math", "05-waterfall-rendering")
import samples  # noqa: E402
from entry import parse_entry  # noqa: E402
from stream import walk  # noqa: E402
from waterfall import bar, critical_path, end_of, render  # noqa: E402


def load(doc):
    data = json.dumps(doc).encode()
    return [parse_entry(i, raw) for kind, i, raw in walk(io.BytesIO(data)) if kind == "entry"]


entries = load(samples.chrome_like())
text = render(entries, width=60)
print(text)
lines = text.splitlines()

# --- geometry ---------------------------------------------------------------------------------------------
# span = 0 .. 2086 ms (the /home request starts at 1905 and takes 181)
assert lines[0].startswith("span 2086 ms, 1 column = 34.8 ms")
rows = {int(l[:3]): l for l in lines[1:]}
assert sorted(rows) == [0, 1, 2, 3, 4, 5]
assert [int(l[:3]) for l in lines[1:]] == [0, 1, 2, 3, 4, 5]    # sorted by start time
scale = 60 / 2086
t0 = entries[0].start
# entry 3 starts 840 ms in: its bar begins at column round(840 * scale) = 24, after the 31-char label
label = len("  3 200 ") + 26 + 1
assert rows[3][label:].startswith(" " * round(840 * scale) + "=")
# 1 ms of send is under a column and vanishes; 900 ms of wait is rounded from CUMULATIVE
# boundaries (1 ms .. 901 ms), so it is 26 columns, and the 9 ms of receive adds none
assert bar(entries[3], t0, scale, 60).count("=") == round(901 * scale) - round(1 * scale) == 26

# a bar is as long as the request, within one column of rounding, however many phases it has
for e in entries:
    b = bar(e, t0, scale, 60)
    first = round((e.start - t0) * scale)
    assert abs((len(b) - first) - e.time * scale) <= 1.01, (e.index, len(b) - first, e.time * scale)

# phases appear in order, each with its letter
b0 = bar(entries[0], t0, scale, 60)
assert b0.index("d") < b0.index("s") < b0.index("=") < b0.index("r")

# a request too short to see still gets a mark
tiny = load({"log": {"entries": [samples.entry(0, "GET", "https://t/a", 200, samples.timings(wait=1), time=1),
                                 samples.entry(1000, "GET", "https://t/b", 200, samples.timings(wait=500))]}})
assert bar(tiny[0], tiny[0].start, 60 / 1500, 60) == "#"

# --- critical path with initiator links ------------------------------------------------------------------------
basis, chain = critical_path(entries)
print("\ncritical path:", basis, [e.index for e in chain])
assert basis == "initiator and redirect links"
# the document -> app.js -> login -> /home (redirect). It ends at 2086; the API chain only reaches 1750.
assert [e.index for e in chain] == [0, 1, 4, 5]
assert end_of(chain[-1]) - chain[0].start == 2086


def mk(i, start, total):
    return samples.entry(start, "GET", f"https://t/{i}", 200, samples.timings(wait=total), time=total)


# --- the fallback without any links: weighted interval scheduling ----------------------------------------------------------
entries2 = load({"log": {"entries": [mk(0, 0, 100), mk(1, 50, 70), mk(2, 130, 70), mk(3, 0, 60)]}})
basis, chain = critical_path(entries2)
assert basis == "timing only"
assert [e.index for e in chain] == [0, 2]        # 100 + 70 busy beats 60 + 70, 70 + 70 (#1 overlaps #0 and #3)

print("module 05 ok")
