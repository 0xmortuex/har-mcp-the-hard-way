# Break It: Streaming JSON

## Challenge 1: Forget that a decode failure may mean "read more"

In `Reader.value`, change the `except json.JSONDecodeError` branch to always
`raise StreamError(...)`. Run module 02. It fails on the first chunk-size test: why does it work
with the default 1 MiB chunk on the *small* sample but fail with 64 bytes?

## Challenge 2: Do not double the read size

Change `want = max(want * 2, self.chunk)` to `want = self.chunk`. With the default chunk the
correctness tests still pass. Make `samples.write_big` produce one entry with a 20 MB body (or use
`Reader(fh, chunk=1024)` on a 5 MB body) and time it. How many times is `raw_decode` retried,
and what does that do to the running time? (Quadratic: each retry re-scans from the start.)

## Challenge 3: Skip the number check

Delete the "number touching the end of the buffer" block in `Reader.value`. The module 02 test
with chunk size 1 may or may not catch it; write the smallest document that does
(hint: a number as the *last* thing before the buffer ends, such as `"entries": [{"a": 12345}]`
read 2 bytes at a time).

## Challenge 4: Decode each chunk separately

Replace the incremental decoder with `data.decode("utf-8")`. Which test fails, and with what error?
(The `é 中文` characters in the test document are 2 and 3 bytes long.)
