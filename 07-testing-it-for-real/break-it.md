# Break It: Testing It for Real

## Challenge 1: A sweep that plants nothing

In `main.py` module 07, empty `samples.SECRETS` (set it to `[]` for the sweep only). The test passes
and proves nothing. Which assertion exists to prevent this, and why does it use `all(...)` over the
file text instead of trusting the list?

## Challenge 2: Collect the whole file

In `server.load`, nothing is wrong: it builds `Entry` records. Now change `walk` in module 02 to
`entries = list(elements(r))` before yielding. Does module 02's correctness test fail? Does module 07's
scale test? By how much does the peak change with `--big`?

## Challenge 3: A new kind of secret

Add `"x-refresh": "FAKEREFRESH999"` to a header in `samples.chrome_like()` and to `SECRETS`.
Run module 07. It fails the leak sweep. Fix `redact.py` (what is the most general fix?) without
touching the sweep.

## Challenge 4: A hostile file that crashes

Add `'{"log": {"entries": [{"request": 5, "response": {}}]}}'` to the hostile list. Does `parse_entry`
survive? If it raises `AttributeError`, how does module 07 report it, and why is that better than
catching `Exception` in the test?

## Challenge 5: Remove the seed

Make the fuzz use `random.Random()` with no seed and break `Reader.value`'s number check. The suite fails
intermittently. Why is a failure you cannot reproduce worse than no test, and what does printing the seed
buy you?
