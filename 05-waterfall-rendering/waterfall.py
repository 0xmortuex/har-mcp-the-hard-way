"""Module 05: an ASCII waterfall and the critical path.

A waterfall is a bar chart where the x axis is time. Every request is one row; the bar
starts at (request start - capture start) and is as long as the request, split into its
phases, each drawn with its own letter:

    . blocked   d dns   c connect   s tls   > send   = wait   r receive

The only real work is converting milliseconds to columns without drifting. We round
CUMULATIVE phase boundaries, not each phase on its own, so rounding errors cannot add up
to a bar that is longer or shorter than the request.

The critical path answers "what chain of requests decided when loading finished?".
"""

from __future__ import annotations

import bisect
from collections import defaultdict
from urllib.parse import urljoin

from entry import Entry
from timing import PHASES, phases, total

CHAR = {"blocked": ".", "dns": "d", "connect": "c", "ssl": "s", "send": ">", "wait": "=", "receive": "r"}


def end_of(e: Entry) -> float:
    assert e.start is not None
    return e.start + total(e.time, e.timings)


def bar(e: Entry, t0: float, scale: float, width: int) -> str:
    """One row's bar: spaces up to the start column, then the phases."""
    assert e.start is not None
    cells = [" "] * (width + 1)
    first = round((e.start - t0) * scale)
    elapsed = 0.0
    p = phases(e.timings)
    drawn = False
    for name in PHASES:
        if p[name] <= 0:
            continue
        a = first + round(elapsed * scale)
        elapsed += p[name]
        b = first + round(elapsed * scale)             # cumulative: no drift
        for col in range(a, min(b, width + 1)):
            cells[col] = CHAR[name]
            drawn = True
    if not drawn and first <= width:                    # too short to see: still show one mark
        cells[first] = "#"
    return "".join(cells).rstrip()


def render(entries: list[Entry], width: int = 60) -> str:
    placed = sorted((e for e in entries if e.start is not None), key=lambda e: (e.start, e.index))
    t0 = placed[0].start
    span = max(max(end_of(e) for e in placed) - t0, 1.0)
    scale = width / span
    lines = [f"span {span:g} ms, 1 column = {span / width:.1f} ms   (. blocked  d dns  c connect  s tls  > send  = wait  r receive)"]
    for e in placed:
        name = e.url.split("://", 1)[-1]
        name = name if len(name) <= 26 else name[:23] + "..."
        lines.append(f"{e.index:>3} {e.status:>3} {name:<26} {bar(e, t0, scale, width)} {total(e.time, e.timings):g} ms")
    return "\n".join(lines)


def redirect_target(e: Entry) -> str:
    return urljoin(e.url, e.redirect_url) if 300 <= e.status < 400 and e.redirect_url else ""


def critical_path(entries: list[Entry]) -> tuple[str, list[Entry]]:
    """Follow parent links (a redirect, else the initiator) from every request back to a root;
    the critical path is the chain with the longest wall-clock from its first request's start
    to its last request's end.

    If the file has no such links (most non-Chrome tools do not record initiators), fall back
    to weighted interval scheduling: the set of NON-overlapping requests with the most busy
    time, solved with dynamic programming."""
    placed = [e for e in entries if e.start is not None]
    by_url = defaultdict(list)
    redirected_to = defaultdict(list)
    for e in placed:
        by_url[e.url].append(e)
        if redirect_target(e):
            redirected_to[redirect_target(e)].append(e)
    parent: dict[int, Entry] = {}
    for e in placed:
        via_redirect = [r for r in redirected_to[e.url] if r.index < e.index]
        if via_redirect:
            parent[e.index] = max(via_redirect, key=lambda r: r.index)
        elif e.initiator_url:
            earlier = [x for x in by_url[e.initiator_url] if x.index != e.index and x.start <= e.start]
            if earlier:
                parent[e.index] = max(earlier, key=lambda x: (x.start, x.index))
    if parent:
        best: list[Entry] = []
        best_span = -1.0
        for e in placed:
            chain, seen = [e], {e.index}
            while chain[-1].index in parent and parent[chain[-1].index].index not in seen:
                chain.append(parent[chain[-1].index])
                seen.add(chain[-1].index)
            chain.reverse()
            span = end_of(chain[-1]) - chain[0].start
            if span > best_span or (span == best_span and len(chain) > len(best)):
                best, best_span = chain, span
        return "initiator and redirect links", best
    # --- fallback: weighted interval scheduling ---
    order = sorted(placed, key=lambda e: (end_of(e), e.index))
    ends = [end_of(e) for e in order]
    best_sum = [0.0] * (len(order) + 1)
    prev = [0] * len(order)
    take = [False] * len(order)
    for i, e in enumerate(order):
        prev[i] = bisect.bisect_right(ends, e.start, 0, i)      # how many requests finished before e began
        with_e = total(e.time, e.timings) + best_sum[prev[i]]
        take[i] = with_e > best_sum[i]
        best_sum[i + 1] = with_e if take[i] else best_sum[i]
    chain, i = [], len(order)
    while i > 0:
        if take[i - 1]:
            chain.append(order[i - 1])
            i = prev[i - 1]
        else:
            i -= 1
    return "timing only", chain[::-1]
