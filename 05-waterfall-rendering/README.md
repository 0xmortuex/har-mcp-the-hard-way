# Module 05: Waterfall Rendering

## The concept

A waterfall is a bar chart whose x axis is time and whose rows are requests. For an agent it is
the fastest way to see *shape*: a long staircase means requests are chained, a wide block means
many ran in parallel, a gap means the browser was idle waiting for something.

```
span 2086 ms, 1 column = 34.8 ms   (. blocked  d dns  c connect  s tls  > send  = wait  r receive)
  0 200 example.com/               ds======r 316 ms
  1 200 example.com/app.js                  ===rrrrrrrrrrr 503 ms
  3 200 example.com/api/data?ap...                         ========================== 910 ms
  4 302 example.com/login                                                             ===r 140 ms
```

It is plain text on purpose: a model reads it in the tool result, a human reads it in a terminal
or a bug report, and there is no image to render.

## Converting milliseconds to columns

`scale = width / span`. A request starting `s` ms after the capture began starts at column
`round(s * scale)`. The trap is **rounding drift**. If you round each phase's length separately,
five phases that each round up make the bar longer than the request. So we round **cumulative
boundaries**: phase k occupies columns `round(offset_k * scale)` to `round(offset_{k+1} * scale)`.
Total length is then `round(total * scale)` within one column, always.

A request too short to occupy a column would vanish, and an invisible request looks like a
missing request, so it gets a single `#`.

## Critical path

"What decided when loading finished?" is the question the waterfall alone cannot answer, because
bars overlap. The critical path is the *chain of dependent requests* that finished last.

**With initiator information (Chrome):** each request has a parent: the request that was
redirected to it, or else the one named by `_initiator`. Follow parent links from every request to
its root; the critical path is the chain with the longest wall-clock from first start to last
end. On the sample, `document → app.js → login → /home` ends at 2086 ms, while the API chain
`document → app.js → api/data` stops at 1750 ms, so the former wins even though the API call is
the single slowest request.

**Without it (Firefox, Safari, mitmproxy, Postman):** we cannot know dependencies, so we answer a
different, honest question: *which set of non-overlapping requests contains the most busy time?*
That is weighted interval scheduling, solvable by dynamic programming: sort by end time; for each
request, `best[i] = max(skip it, its duration + best[number of requests that ended before it began])`,
using `bisect` to find that number. The output says which method was used (`basis`), because a
guess presented as a fact is worse than no answer.

## The code

- `waterfall.py` — `bar`, `render`, `critical_path`.
- `main.py` — asserts the header line, the row order, the exact start column of one bar, the
  exact number of `=` characters in another (26, from cumulative rounding), that every bar's length is
  within a column of the request's duration, that phases appear in order, the `#` mark, the chain
  `[0, 1, 4, 5]` with `basis == "initiator and redirect links"`, and the fallback on a hand-made case
  where the best chain is `[0, 2]`.

```bash
python 05-waterfall-rendering/main.py
```

Next: [Module 06](../06-mcp-wrapper) — putting it behind MCP.
