# Module 04: Redaction Design

## The concept

A HAR is a recording of everything your browser sent. That means session cookies, `Authorization`
headers, OAuth codes in redirect URLs, API keys in query strings, passwords in login POST bodies.
If an MCP server hands the file to a model unfiltered, the secrets go to the model provider, into
transcripts, and into whatever the model writes next. So the default must be **masked output**, and
the guarantee must be **tested**, not hoped for.

A masked value becomes `<redacted:31>`: the value is gone, its length stays. That keeps the
analysis useful (a 36-character value is a UUID; a 900-character one is a JWT; "present but empty"
is different from "present") without exposing it.

## Three layers, because one is never enough

1. **By name.** Headers, cookies, query parameters, form fields and JSON keys whose *name* says
   "secret": authorization, cookie, token, password, api_key, session, csrf, signature... Whatever
   the value looks like, it goes. This catches most things and is the easiest to get right.
2. **By shape.** A JWT (`eyJ...`), a GitHub token (`ghp_...`), an AWS key (`AKIA...`) is a secret
   even in a header called `X-Custom`. Regexes for well-known credential formats.
3. **By context in free text.** A response body that is not JSON or a form can still contain
   `password=hunter2`. A regex over `name=value` and `"name": "value"` with secret-sounding names.

## The traps we hit

- **Pseudo-headers.** HTTP/2 headers like `:authority` contain "auth". Masking the host is a bug that
  makes the output useless. Names starting with `:` are exempt. The same for
  `access-control-allow-credentials: true`.
- **`author` vs `authorization`.** A naive `auth` match masks "Author". The pattern is
  `auth(?!or(?!iz))`: not followed by "or" unless the "or" is followed by "iz". Test names on both sides.
- **OAuth puts tokens in the URL fragment**: `https://app/cb#access_token=...`. Parse the fragment too.
- **`user:password@host`** in URLs.
- **Idempotence.** Masking a masked value must change nothing, or `<redacted:3>` becomes
  `<redacted:12>`. Then redacting twice gives a different file, and a "defence in depth" pass becomes
  corruption. The fix is one line: `mask()` returns an already-masked value as it is.
- **Cookies.** A `Cookie` header is `a=1; b=2`: mask each value, keep the names. A `Set-Cookie`
  is the same for the first pair; keep the attributes (`Path`, `HttpOnly`) because they are not secret.
- **Authorization** keeps its scheme: `Bearer <redacted:31>` still tells you the auth type.
- **Input is never modified.** `redact()` builds a new structure. Sharing a mutated cache between
  a "show me raw" call and a "show me masked" call is how secrets leak.

## What it cannot do (say so)

A secret with an innocent name and shape, in a URL path segment or an HTML page, is not
recognised. Binary bodies cannot be inspected. The server's README says this plainly, because a
tool that claims more than it does is worse than none.

## The code

- `redact.py` — `mask`, `sensitive`, `scrub_text`, `mask_url`, `mask_header`, `redact_body`, and
  `redact`, which walks any JSON value (a whole HAR, an entry, a body).
- `main.py` — plants the fake secrets from `samples.py`, redacts the whole HAR, and asserts that
  (a) none of them survive anywhere in the serialized output, (b) the input was not modified,
  (c) timings, statuses and times are unchanged, so the redacted file is still useful, and
  (d) `redact(redact(x)) == redact(x)`.

```bash
python 04-redaction-design/main.py
```

Next: [Module 05](../05-waterfall-rendering) — drawing the timeline.
