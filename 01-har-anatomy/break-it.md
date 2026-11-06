# Break It: HAR Anatomy

## Challenge 1: Trust `fromisoformat`

Replace the body of `parse_iso_ms` with
`datetime.fromisoformat(text).timestamp() * 1000` and run module 01. If you have Python 3.10,
the trailing `Z` is rejected outright (3.11+ accepts it). On any version, look at the offset
test: what zone does `.timestamp()` assume for a string with no zone, and why is that a bug for
a tool that compares timestamps from files recorded on different machines?

## Challenge 2: Treat `-1` and `None` as numbers

In `number()`, delete the `isinstance` check and just `return float(value)`. Run module 01.
Which assertion fails, and on what input? (Hint: the nearly-empty entry at the end has no
`time` at all.) The lesson: HAR numbers are optional, so "convert and hope" is not a parser.

## Challenge 3: Assume `status` is an int

Change `status_code` to `return int(value)` without the `try`. Which input in `main.py` breaks it?
Which real tool produces that input?

## Challenge 4: Crash on a missing key

Change `resp = raw.get("response") or {}` to `resp = raw["response"]`. A real HAR from a request
that was cancelled before any response may have no `response` at all. What does the *agent*
see when the tool crashes with `KeyError: 'response'`? Compare with what module 06 shows for a
`ValueError`.
