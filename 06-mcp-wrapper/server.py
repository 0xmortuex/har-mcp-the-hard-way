"""Module 06: wrap everything in an MCP server.

Four tools, the minimal version of har-mcp:

    har_overview      what is in the file?
    slowest_requests  what is slow, and why?
    waterfall         timeline + critical path
    redact_har        write a safe-to-share copy

Three design rules, each of which cost somebody a bug:

1. Failures an agent can act on must be raised as ToolError. The MCP SDK sends a client
   ONLY a ToolError's message; any other exception arrives as "Error executing tool X",
   which tells the model nothing.
2. Secrets are masked by default. A tool that prints a URL prints mask_url(url).
3. The server only touches files under --dir, symlinks resolved, so a prompt-injected
   "read C:/Users/me/.ssh/id_rsa" fails.
"""

from __future__ import annotations

import argparse
import functools
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import modpath  # noqa: E402

modpath.use("01-har-anatomy", "02-streaming-json", "03-timing-math", "04-redaction-design", "05-waterfall-rendering")

from entry import Entry, parse_entry  # noqa: E402
from mcp.server.mcpserver import MCPServer  # noqa: E402
from mcp.server.mcpserver.exceptions import ToolError  # noqa: E402
from redact import mask_url, redact  # noqa: E402
from stream import StreamError, walk  # noqa: E402
from timing import describe, total  # noqa: E402
from waterfall import critical_path, render  # noqa: E402

mcp = MCPServer(
    "harlite",
    instructions="Analyze HAR files. Start with har_overview. URLs are masked: secrets show as <redacted:N>.",
)
ALLOWED: list[str] = []


def inside(path: str, root: str) -> bool:
    a, b = os.path.normcase(path), os.path.normcase(root)
    try:
        return os.path.commonpath([a, b]) == b
    except ValueError:  # different drives on Windows
        return False


def resolve(path: str) -> str:
    """Relative paths start at the first --dir. realpath resolves symlinks and '..'
    BEFORE we compare, which is the whole point."""
    full = path if os.path.isabs(path) else os.path.join(ALLOWED[0], path)
    real = os.path.realpath(full)
    if not any(inside(real, root) for root in ALLOWED):
        raise ValueError(f"{path!r} is outside the allowed directories ({'; '.join(ALLOWED)}); restart with --dir <folder>")
    return real


def tool(fn):
    """Register fn as a tool, turning the errors an agent can fix into ToolErrors."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (ValueError, OSError, StreamError) as e:  # not a blanket except: real bugs stay loud
            raise ToolError(str(e)) from e

    mcp.tool()(wrapper)
    return fn


def load(path: str) -> list[Entry]:
    real = resolve(path)
    if not os.path.isfile(real):
        raise FileNotFoundError(f"no such file: {real}")
    with open(real, "rb") as fh:
        return [parse_entry(i, raw) for kind, i, raw in walk(fh) if kind == "entry"]


@tool
def har_overview(path: str) -> str:
    """Summarize a HAR: entry count, time range, totals by status class and domain."""
    es = load(path)
    if not es:
        return "No entries."
    classes: dict[str, int] = {}
    domains: dict[str, int] = {}
    for e in es:
        key = "no response" if e.status <= 0 else f"{e.status // 100}xx"
        classes[key] = classes.get(key, 0) + 1
        host = e.url.split("://", 1)[-1].split("/", 1)[0]
        domains[host] = domains.get(host, 0) + 1
    ends = [e.start + total(e.time, e.timings) for e in es if e.start is not None]
    starts = [e.start for e in es if e.start is not None]
    span = f"{max(ends) - min(starts):g} ms" if starts else "unknown"
    return (
        f"{len(es)} entries, span {span}, transferred {sum(e.transfer for e in es):,.0f} B\n"
        f"By status: {', '.join(f'{k}: {v}' for k, v in sorted(classes.items()))}\n"
        f"By domain: {', '.join(f'{k}: {v}' for k, v in sorted(domains.items(), key=lambda kv: -kv[1])[:10])}"
    )


@tool
def slowest_requests(path: str, limit: int = 5) -> str:
    """Slowest requests by total time, each with its phase breakdown and what dominates."""
    if not 1 <= limit <= 100:
        raise ValueError(f"limit must be between 1 and 100, got {limit}")
    es = sorted(load(path), key=lambda e: (-total(e.time, e.timings), e.index))[:limit]
    out = []
    for e in es:
        out.append(f"#{e.index} {e.method} {e.status} {total(e.time, e.timings):g} ms {mask_url(e.url)}")
        out.append("    " + describe(e.timings).replace("\n", "\n    "))
    return "\n".join(out)


@tool
def waterfall(path: str, width: int = 60) -> str:
    """ASCII timeline of the load plus the critical path."""
    es = load(path)
    if not any(e.start is not None for e in es):
        raise ValueError("no entry has a usable startedDateTime, so a timeline cannot be drawn")
    for e in es:
        e.url = mask_url(e.url)                # mask before rendering: render() just prints what it is given
    basis, chain = critical_path(es)
    return render(es, width) + f"\n\nCritical path ({basis}): " + " -> ".join(f"#{e.index}" for e in chain)


@tool
def redact_har(path: str, output: str) -> str:
    """Write a sanitized copy of a HAR. Never overwrites an existing file."""
    src, dst = resolve(path), resolve(output)
    if src == dst:
        raise ValueError("output must differ from the input")
    if not os.path.isfile(src):
        raise FileNotFoundError(f"no such file: {src}")
    # "x" = exclusive create: it fails if the file exists. Checking os.path.exists first
    # and then opening with "w" would race; "x" makes the check and the create one step.
    out = open(dst, "x", encoding="utf-8", newline="\n")
    try:
        with out, open(src, "rb") as fin:
            out.write('{"log":{"entries":[')
            n = 0
            meta = {}
            for kind, key, value in walk(fin):
                if kind == "entry":
                    out.write(("," if n else "") + json.dumps(redact(value), separators=(",", ":")))
                    n += 1
                else:
                    meta[key] = redact(value, key)
            # JSON objects are unordered, so version/creator/pages can follow the entries.
            members = json.dumps(meta)[1:-1]            # '"version": "1.2", ...' without the braces
            out.write("]" + ("," + members if members else "") + "}}")
    except BaseException:
        os.remove(dst)                     # the partial file is ours: "x" just created it
        raise
    return f"Wrote {dst}: {n} entries"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", action="append", default=[], help="allowed folder (repeatable)")
    args = parser.parse_args()
    ALLOWED.extend(os.path.realpath(d) for d in (args.dir or [os.getcwd()]))
    mcp.run()


if __name__ == "__main__":
    main()
