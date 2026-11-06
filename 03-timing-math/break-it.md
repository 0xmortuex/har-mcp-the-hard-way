# Break It: Timing Math

## Challenge 1: Add all seven phases

In `phases()`, delete the `p["connect"] -= p["ssl"]` line. Which assertion fails, and by how many
milliseconds? Would a casual look at the output of `describe()` reveal it?

## Challenge 2: Let `-1` through

In `ms()`, return `float(value)` instead of clamping at 0 (`max(..., 0.0)`). Which assertion catches
it? What would the dominant phase of a reused-connection request look like?

## Challenge 3: Always sum

Make `total()` ignore the `time` argument. The sample data still agrees with itself (its `time`
fields equal the phase sums), so only one assertion in `main.py` fails. Which, and what real
situation does it stand for? (Think: HTTP/2 push, retries, or a tool that measures from a different starting point.)

## Challenge 4: Break the tie

`dominant({"dns": 10, "wait": 10})` returns `dns`. Change `max(PHASES, key=...)` so ties go to the
later phase. One assertion fails. Is pinning a tie-break worth a test line? Argue both sides: the
rule is arbitrary, but an agent that gets a different answer on the same file between versions is
harder to trust.
