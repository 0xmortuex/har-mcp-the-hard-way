"""Module 06: run the server for real, over stdio, and call its tools like an MCP client does."""

import asyncio
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import modpath  # noqa: E402

modpath.use()
import samples  # noqa: E402
from mcp import ClientSession  # noqa: E402
from mcp.client.stdio import StdioServerParameters, stdio_client  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


async def main() -> None:
    allowed = tempfile.mkdtemp()
    outside = tempfile.mkdtemp()
    har = samples.write(os.path.join(allowed, "site.har"), samples.chrome_like())
    other = samples.write(os.path.join(outside, "other.har"), samples.chrome_like())
    env = dict(os.environ, PYTHONIOENCODING="utf-8")     # Windows consoles default to cp1252
    params = StdioServerParameters(command=sys.executable, args=[os.path.join(HERE, "server.py"), "--dir", allowed], env=env)

    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        tools = {t.name for t in (await session.list_tools()).tools}
        print("tools:", sorted(tools))
        assert tools == {"har_overview", "slowest_requests", "waterfall", "redact_har"}

        async def call(name, **args):
            res = await session.call_tool(name, args)
            return res.is_error, res.content[0].text

        err, text = await call("har_overview", path="site.har")           # relative: starts at --dir
        assert not err and text.startswith("6 entries, span 2086 ms"), text
        assert "2xx: 5" in text and "3xx: 1" in text

        err, text = await call("slowest_requests", path=har, limit=2)
        print(text)
        assert not err
        assert text.splitlines()[0] == "#3 GET 200 910 ms https://example.com/api/data?api_key=<redacted:20>&page=2"
        assert "dominated by wait (99%)" in text

        err, text = await call("waterfall", path=har)
        assert not err and text.endswith("Critical path (initiator and redirect links): #0 -> #1 -> #4 -> #5"), text

        # --- redact_har: writes a clean copy, once ---
        out = os.path.join(allowed, "clean.har")
        err, text = await call("redact_har", path=har, output=out)
        assert not err and "6 entries" in text, text
        clean = open(out, encoding="utf-8").read()
        assert len(json.loads(clean)["log"]["entries"]) == 6
        assert json.loads(clean)["log"]["version"] == "1.2"
        for secret in samples.SECRETS:
            assert secret not in clean, secret

        # --- every output, default settings: no secret may appear ---
        for name, args in [("har_overview", {"path": har}), ("slowest_requests", {"path": har, "limit": 6}), ("waterfall", {"path": har})]:
            err, text = await call(name, **args)
            assert not err
            for secret in samples.SECRETS:
                assert secret not in text, (name, secret)

        # --- errors reach the model with an instruction it can act on ---
        err, text = await call("redact_har", path=har, output=out)
        assert err and "exists" in text, text                                 # never overwrites
        err, text = await call("har_overview", path=other)
        assert err and "outside the allowed directories" in text and "--dir" in text, text
        err, text = await call("har_overview", path="nope.har")
        assert err and "no such file" in text, text
        err, text = await call("slowest_requests", path=har, limit=0)
        assert err and "limit must be between 1 and 100" in text, text
        bad = os.path.join(allowed, "bad.har")
        open(bad, "w", encoding="utf-8").write('{"log": {"entries": [{"a"')
        err, text = await call("har_overview", path=bad)
        assert err and "invalid JSON" in text, text

    print("module 06 ok")


asyncio.run(main())
