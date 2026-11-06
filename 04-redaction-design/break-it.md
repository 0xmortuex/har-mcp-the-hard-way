# Break It: Redaction Design

## Challenge 1: Drop the shape layer

In `SHAPES`, remove the JWT alternative (keep the others). Which planted secret leaks, and
through which header? This is the reason names alone are not enough.

## Challenge 2: Lose idempotence

Change `mask()` to `return f"<redacted:{len(value)}>"` (no `ALREADY` check). Which assertion
fails? Work out by hand what `mask("<redacted:20>")` returns.

## Challenge 3: Forget the fragment

In `mask_url`, delete the `if hash_:` block. Which assertion notices? It is one of the hand-written edge cases, **not** the planted-secret
sweep, because the sample has no fragment token. Add a fake `#access_token=...` URL to
`samples.chrome_like()` and a `SECRETS` entry and watch the sweep fail too. A sweep only protects
what you planted: plant first, then fix.

## Challenge 4: Match `auth` naively

Replace `auth(?!or(?!iz))` with `auth`. Which assertion in `main.py` fails, and for which input?
Then also delete the `startswith(":")` exemption and think about what masking `:authority`
would do to every HTTP/2 request in a capture.

## Challenge 5: Mutate in place

Change `redact()` so that the `{"name": ..., "value": ...}` branch does `obj["value"] = masked` and
returns `obj`. Run module 04. Which assertion catches the shared mutation?
