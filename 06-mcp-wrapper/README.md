# Module 06: The MCP Wrapper

## The concept

MCP is JSON-RPC over a pipe. For a local server the client (Claude Desktop, Claude Code) launches
your program as a subprocess and talks to it over stdin/stdout:

```
client                                         your server
initialize             ───────────────────────►
                       ◄───────────────────────  name, capabilities
tools/list             ───────────────────────►
                       ◄───────────────────────  [{name, description, inputSchema}, ...]
tools/call har_overview {"path": "site.har"} ─►
                       ◄───────────────────────  {content: [{text: "..."}], isError: false}
```

The SDK does the protocol. Your job is the part the SDK cannot do: **tool design** and
**safe failure**. Everything so far (modules 01–05) is plain Python with no MCP in it, which is why
the wrapper is under 200 lines and why you could test the logic without a client.

## Three rules

**1. Errors must be `ToolError` to reach the model.** The SDK sends a client only a `ToolError`'s
message. Any other exception arrives as `Error executing tool X` and the model learns nothing, so it
retries blindly. The `@tool` decorator converts the failures an agent can fix (`ValueError`,
`OSError`, `StreamError`) into `ToolError` and leaves everything else alone, because an unexpected
`KeyError` is a *bug*, and hiding bugs behind friendly messages is how they survive. Note the decorator
registers the wrapper but returns the original function, so unit tests call the plain function and see the
raw exception (module 07 uses this).

**2. Default to masked.** Every URL a tool prints goes through `mask_url`. There is no flag in
this minimal version to turn it off. (The full server has an `include_secrets` argument,
default false.) `waterfall` masks URLs *before* rendering: the renderer just prints what it is given,
so it cannot leak what it never received.

**3. A sandbox.** The server only touches files under `--dir`. `resolve()` calls
`os.path.realpath` *before* comparing, which collapses `..` and follows symlinks; checking the
string first and resolving later is the classic escape. `redact_har` also never overwrites: it opens
the output with mode `"x"` (exclusive create), which makes "does it exist?" and "create it" one atomic
step. `os.path.exists()` followed by `open(..., "w")` has a gap you can drive a race through. If
writing fails halfway, the partial file (which the `"x"` mode guarantees is ours) is removed.

## Tool descriptions are the interface

The docstring is what the model reads to decide when to call the tool. "Summarize a HAR: entry count,
time range, totals by status class and domain" tells it this is the first call. Vague descriptions
get tools misused. Parameters have defaults and range checks with messages that say what is allowed
(`limit must be between 1 and 100, got 0`).

## The code

- `server.py` — the four tools, the sandbox, the decorator.
- `main.py` — launches `server.py` as a **real subprocess over stdio** using the SDK's own
  client, lists the tools, calls each, and checks: exact output of `slowest_requests` (URL masked),
  the critical path string, a redacted file with none of the planted secrets in it, never-overwrites, the
  sandbox refusing a file outside `--dir`, a nonexistent file, an out-of-range limit and a truncated HAR.
  Each of those errors comes back with `is_error` true and a message that tells you what to do.

```bash
python 06-mcp-wrapper/main.py
```

To use it from Claude Code: `claude mcp add harlite -- python /full/path/06-mcp-wrapper/server.py --dir /path/to/hars`.

Next: [Module 07](../07-testing-it-for-real) — proving it holds up.
