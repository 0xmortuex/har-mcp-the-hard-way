# Module 02: Streaming JSON

## The concept

`json.load` parses the whole file and builds every object in Python. A Python `dict` or `str`
costs several times its size in the file, so a 200 MB HAR needs well over a gigabyte. Even if it
fits, you pay it again on every tool call unless you cache the whole tree. We want constant
memory: **one entry alive at a time**.

Python has no streaming JSON parser in the standard library. The usual answer is `ijson`, a
dependency. You do not need one, because HAR has a simple skeleton and the standard library
has the one primitive you need: `json.JSONDecoder.raw_decode(text, pos)` decodes **one value
starting at `pos`** and tells you where it ended, using the fast C scanner.

So we walk the skeleton by hand, and let `raw_decode` do the heavy lifting one entry at a time:

```
{ "log" : { "version": ..., "entries" : [  e0  ,  e1  ,  e2  ...  ] , "pages": ... } }
  ^members()   ^members()                  ^elements() yields each entry via raw_decode
```

## The one subtlety

We read the file in chunks (1 MiB). An entry may straddle the end of our buffer.
`raw_decode` cannot distinguish "this is cut off" from "this is invalid": both raise
`JSONDecodeError`. So:

- on failure, **read more and retry** (doubling the read each time, so one 50 MB entry costs a
  handful of reads, not 50 thousand);
- only when the file is exhausted is a failure a real error.

Two more places the chunk boundary bites, both handled in `Reader`:

- **Numbers.** `12` at the very end of the buffer might really be `123`. `raw_decode` happily
  returns 12. If a value ends exactly at the buffer end and might be a number, read more first.
- **Multi-byte characters.** A UTF-8 character can be split between two reads. We use an
  *incremental* decoder (`codecs.getincrementaldecoder`), which holds the partial bytes until
  the rest arrive. `utf-8-sig` also strips the byte-order mark that Postman writes.

## The code

- `stream.py` — `Reader` (buffer, `peek`, `value`), `members`, `elements`, and `walk(fh)`
  which yields `("log", name, value)` for the small metadata and `("entry", i, dict)` for each
  request.
- `main.py` — (1) compares the stream with `json.load` at chunk sizes 1, 2, 3, 7, 64, ...
  (2) builds a 20 MB file and measures peak memory with `tracemalloc` for both approaches;
  (3) checks the error messages for truncated and wrong-shaped files.

```bash
python 02-streaming-json/main.py
```

Typical output:

```
json.load : peak    43.7 MB    0.1 s
stream    : peak     4.2 MB    0.2 s
```

The stream's peak is flat: make the file 5x bigger and it stays at ~4 MB, while `json.load`
grows 5x. (Real HARs have deeper nesting than our sample, so `json.load`'s overhead is worse
than shown.)

## Design notes

- `walk` yields entries and a **cheap summary** is kept per entry (module 01's `Entry`), not
  the raw dict. A tool that needs headers or a body for ONE request streams the file again to
  entry N and keeps just that one.
- Errors are explicit: `StreamError("not a HAR file: there is no top-level 'log' member")`.
  A truncated download says "invalid JSON", it does not return half the entries silently.

Next: [Module 03](../03-timing-math) — the numbers inside each entry.
