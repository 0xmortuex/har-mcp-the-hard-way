# Module 03: Timing Math

## The concept

"Which request is slowest, and why?" is the question an agent asks most. It has an exact answer
only if the arithmetic is right, and HAR timing has three traps.

Each entry has seven phases, in the order they happen:

```
blocked  dns  connect  ssl  send  wait  receive
 queue   name  TCP      TLS  upload server download
         lookup handshake         think time (TTFB)
```

**Trap 1: `-1` is not a duration.** It means "this phase did not happen". A request on a reused
connection has no dns, connect or ssl. Some tools omit the key. Both mean 0 ms. If you add `-1`s
into a total you get nonsense that is off by a few milliseconds, which is the worst kind: plausible.

**Trap 2: `ssl` is inside `connect`.** The HAR 1.2 spec says `connect` "includes ssl", and Chrome
follows it. A request with `connect: 40, ssl: 30` spent 10 ms on TCP and 30 ms on TLS. Sum all
seven numbers and you count the handshake twice. `phases()` fixes it by reporting TCP and TLS
separately and making the sum come out right. A tool that reports `ssl` *larger* than `connect`
is evidently putting it outside, so we leave both alone and add both.

**Trap 3: the total.** `time` is the request's total and should equal the phase sum. We trust it
when present, and sum the phases when the tool did not write it.

## Dominant phase

"What dominates?" is just the biggest phase over the sum of phases. The useful part is the hint
that goes with it, because it tells an agent what to investigate:

| dominant | meaning | look at |
|---|---|---|
| wait | server was slow to answer | the backend, not the network |
| receive | payload large or link slow | compression, size, lazy loading |
| blocked | queued behind other requests | connection limits, request priority |
| dns / connect / ssl | connection setup | preconnect, keep-alive, CDN |

## The code

- `timing.py` — `ms`, `phases`, `total`, `dominant`, `describe`.
- `main.py` — pulls entries through modules 01 and 02 and asserts exact values: the first
  request's phases are `{blocked 5, dns 20, connect 10, ssl 30, send 1, wait 200, receive 50}`
  summing to exactly the `time` field (316), the slow API call is 99% `wait`, `app.js` is 80%
  `receive`, and the edge cases (missing keys, string values, `ssl > connect`) behave.

```bash
python 03-timing-math/main.py
```

Next: [Module 04](../04-redaction-design) — what to do about the secrets in the file.
