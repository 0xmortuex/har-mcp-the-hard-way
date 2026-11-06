# HAR MCP — The Hard Way

Build an MCP server that lets an AI agent debug web performance from a browser's HAR export.
Start from the raw JSON and end with an agent that can say "this request is slow because the
server took 900 ms to answer, and here is the chain of requests that decided your load time",
without ever being shown a password.

At the end you will have built a minimal version of
[har-mcp](https://github.com/0xmortuex/har-mcp) yourself, and you will understand the three
things most MCP tutorials skip: **reading data too big for memory**, **timing numbers that
look simple and are not**, and **handing a model a file full of secrets safely**.

## Why this exists

Most MCP tutorials stop at a weather API. The hard part of a useful server is elsewhere:

- a HAR file is 10–200 MB of nested JSON; `json.load` would need gigabytes
- the numbers inside have traps (`-1` means "n/a", `ssl` is inside `connect`)
- the file contains every cookie and bearer token your browser sent
- the model needs the three lines that matter, not 200 MB

## Who it is for

Developers who built a "hello world" MCP server and want a real one. You need Python 3.10+ and
no knowledge of HAR.

## The modules

| # | Module | You build | Proof (`main.py` asserts) |
|---|--------|-----------|---------------------------|
| 01 | [HAR anatomy](01-har-anatomy) | `Entry` parser, timestamp parser | the six facts the rest relies on |
| 02 | [Streaming JSON](02-streaming-json) | an incremental reader | agrees with `json.load` at 1-byte chunks; 20 MB in ~4 MB of RAM |
| 03 | [Timing math](03-timing-math) | phases, totals, dominant phase | exact millisecond arithmetic |
| 04 | [Redaction design](04-redaction-design) | a masker | planted fake secrets never survive; idempotent |
| 05 | [Waterfall rendering](05-waterfall-rendering) | ASCII waterfall + critical path | exact columns, exact chain |
| 06 | [The MCP wrapper](06-mcp-wrapper) | a 4-tool stdio server | called over real MCP, errors reach the client |
| 07 | [Testing it for real](07-testing-it-for-real) | fuzz, leak sweep, scale, hostile files | all four |

Every module is prose (the why), runnable code, and a `main.py` that **checks its own result
with `assert`**. Later modules import the code written in earlier ones, so you build one
server step by step.

## Run it

```bash
pip install -r requirements.txt     # mcp, anyio
python verify.py                    # all seven modules, ~6 seconds
python verify.py 02 04              # just those
python verify.py --big              # module 07 with a 100 MB file
python 03-timing-math/main.py       # or any single module
```

Each module also has a `break-it.md`: changes to make to the code to see exactly which
assertion catches them. Do those; the failures teach more than the passes.

## What is deliberately missing

The finished [har-mcp](https://github.com/0xmortuex/har-mcp) has seven tools (this builds four),
filters, a redirect-chain view, body previews, cache statistics, a `--dir` sandbox with
multiple roots, and a larger test suite. Everything it has that this does not is an elaboration
of something in these seven modules.

## License

MIT
