"""Module 03: HAR timing math.

A HAR entry reports seven phases:

    blocked  dns  connect  ssl  send  wait  receive

and a separate total, `time`. The traps:

* -1 means "this phase did not happen" (a reused connection has no dns/connect/ssl).
  It is not a negative duration. Some tools leave the key out entirely. Both mean 0 ms.
* `ssl` is INSIDE `connect` according to the HAR 1.2 spec (Chrome follows it): a request
  with connect=40 and ssl=30 spent 10 ms on TCP and 30 ms on TLS, not 70 ms connecting.
  Adding all seven numbers would double-count the TLS handshake.
* `time` should equal the sum of the phases (without double counting ssl), but not every
  tool writes it. We trust it when it is there, and sum the phases when it is not.
"""

from __future__ import annotations

from typing import Any

PHASES = ("blocked", "dns", "connect", "ssl", "send", "wait", "receive")

HINTS = {
    "blocked": "queued behind other requests or a connection limit",
    "dns": "slow name resolution",
    "connect": "slow TCP connect: consider preconnect or keep-alive",
    "ssl": "slow TLS handshake",
    "send": "slow upload",
    "wait": "the server was slow to answer (time to first byte): look at the backend",
    "receive": "slow download: payload too large or bandwidth limited",
}


def ms(value: Any) -> float:
    """A phase duration: -1, None, a string or a missing key all become 0."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return max(float(value), 0.0)
    return 0.0


def phases(timings: dict[str, Any]) -> dict[str, float]:
    """The seven phases with `connect` reduced to TCP only (TLS is reported on its own)."""
    p = {name: ms(timings.get(name)) for name in PHASES}
    if p["ssl"] <= p["connect"]:
        p["connect"] -= p["ssl"]            # spec: ssl is part of connect
    # else: a tool that put ssl outside connect. Leave both as they are; both get counted.
    return p


def total(time_field: float, timings: dict[str, Any]) -> float:
    """The request's total: the HAR's own `time` when it has one, else the sum of phases."""
    if time_field >= 0:
        return time_field
    return sum(phases(timings).values())


def dominant(timings: dict[str, Any]) -> tuple[str, float] | None:
    """The biggest phase and its share of all phases, or None if nothing was timed."""
    p = phases(timings)
    whole = sum(p.values())
    if whole <= 0:
        return None
    name = max(PHASES, key=lambda n: p[n])     # ties go to the earlier phase
    return name, p[name] / whole


def describe(timings: dict[str, Any]) -> str:
    p = phases(timings)
    shown = " | ".join(f"{'tls' if k == 'ssl' else k} {v:g} ms" for k, v in p.items() if v > 0)
    dom = dominant(timings)
    if dom is None:
        return shown or "no timing data"
    return f"{shown}\n    dominated by {dom[0]} ({dom[1] * 100:.0f}%): {HINTS[dom[0]]}"
