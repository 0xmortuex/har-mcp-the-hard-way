# Module 07: Testing It for Real

## The concept

Unit tests of pure functions (modules 01–05) are necessary and nowhere near enough. A HAR tool fails
in four ways that need their own kind of test, and each corresponds to a bug that a real server has had.

### 1. Boundaries: fuzz the chunk size

The streaming reader's bugs live where a chunk ends in the middle of a token: a number, an escape
sequence, a multi-byte character. The tests in module 02 try a few hand-picked sizes. Here we
try **400 random chunkings** (seeded, so a failure is reproducible: the assertion message prints the
seed) of a document that deliberately contains unicode, quotes, backslashes, huge integers and nested
empties, compact and indented, and compare each with `json.load`. A property test: *whatever the chunk size,
the result is the same*.

### 2. Leaks: plant, call everything, grep everything

"We mask secrets" is a claim; "none of 7 planted fakes appears in the output of any tool" is a test. The
sweep calls **every tool** and the redacted file, concatenates the output, and greps for each secret. It also
asserts the secrets *are in the input*, because a sweep that plants nothing passes vacuously. When you
add a tool, add it to the sweep. When you find a new kind of secret, plant one first, watch the sweep fail,
then fix the masker.

### 3. Scale: assert on memory and time, not just results

It works on 6 entries and dies on 60,000 is the failure unit tests cannot see. The test writes a
30 MB HAR (100 MB with `--big`, which is what CI's large-file job uses), runs a tool on it, and asserts
peak memory stayed under 40 MB and the *exact* answer (`#49 GET 200 53 ms`: entry i has `wait = i % 50 + 1`,
so the maximum is 50 + 1 send + 2 receive, first reached at i = 49). A streaming reader that quietly
collects every entry into a list passes the correctness check and fails the memory one.

`tracemalloc` measures Python allocations on every OS. The full project measures the child process's
real peak memory with each OS's own counter, because `resource.ru_maxrss` is in **bytes on macOS
and kilobytes on Linux**, and a test that assumes one unit passes on your laptop and fails in CI.

### 4. Hostile files

Empty, truncated, an HTML login page saved as `.har`, valid JSON of the wrong shape, an entry that is
an integer. Every one must give an actionable error, never a traceback. This test found a real bug while
this course was being written: `parse_entry` called `.get` on an integer and crashed with
`AttributeError`, which the `@tool` decorator (rightly) does not convert, so the client would have seen
a bare "Error executing tool". The fix is a `ValueError("entry 0 is not a JSON object")` in module 01.
The test only catches `(StreamError, ValueError, OSError)`: anything else, such as an `AttributeError`,
propagates and fails the run, which is exactly the point.

## The code

`main.py` runs all four. It imports the server from module 06 and calls the tool functions directly
(they are plain functions; the wrapper that makes them MCP tools is separate).

```bash
python 07-testing-it-for-real/main.py          # 30 MB
python 07-testing-it-for-real/main.py --big    # 100 MB
```

## What the real project adds

[har-mcp](https://github.com/0xmortuex/har-mcp) runs the same four ideas at larger scale: 148 tests with
every number hand-computed, planted secrets over *all seven* tools plus a redacted file, a 100 MB test
that measures the child's peak RSS with per-OS code, generated Firefox/Safari/Postman/mitmproxy-shaped
fixtures, and a stdio test that launches the installed server. CI runs it on Linux, macOS and Windows,
and that is where the unit bug above (and others) shows up.

## Where to go from here

- Add `find_requests` with filters (note: filter on the **masked** URL, or a caller can binary-search a
  token through the match count).
- Add `request_detail` with a body preview that is binary-safe.
- Add a `failed_requests` tool that reports `_error` and the initiator.
- Record a real HAR from your own browser, run the server on it, and see what you got wrong.
