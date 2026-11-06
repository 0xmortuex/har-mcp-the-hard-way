# Break It: The MCP Wrapper

## Challenge 1: Print to stdout

Add `print("loading", path)` at the top of `load()` in `server.py` and run module 06. Over stdio,
stdout is the protocol channel, and your line is not JSON-RPC. What does the client do? Now send it
to stderr (`file=sys.stderr`). Why is stderr safe?

## Challenge 2: Let a plain exception through

In the `tool` decorator, change `except (ValueError, OSError, StreamError)` to `except ZeroDivisionError`.
Run module 06 and look at the message the client receives for the missing file. Compare it with the
one you get now. What would a model do after each?

## Challenge 3: Check the path, then resolve it

In `resolve()`, check `inside(full, root)` on the **unresolved** path and only then call `realpath`.
Create a symlink inside the allowed directory that points outside, and call a tool on it. (On Windows
creating symlinks may need Developer Mode.) What does the old code do, and what does the new one?

## Challenge 4: Overwrite

In `redact_har`, open with `"w"` instead of `"x"` after an `os.path.exists` check that you delete.
Run module 06: which assertion fails? Then think about two tool calls arriving at once.

## Challenge 5: Unmasked URL

Remove `mask_url` from `slowest_requests`. Which assertion in module 06 fails, and which in
module 07? (That the two modules disagree about *where* the leak is found is the argument for
having both.)
