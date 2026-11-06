"""Module 04: redaction. Plants fake secrets, redacts, and proves none survive."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import modpath  # noqa: E402

modpath.use("04-redaction-design")
import samples  # noqa: E402
from redact import mask_header, mask_url, redact, redact_body, scrub_text, sensitive  # noqa: E402

doc = samples.chrome_like()
before = json.dumps(doc)
for secret in samples.SECRETS:
    assert secret in before, f"planted secret {secret!r} should be in the input"

clean = redact(doc)
after = json.dumps(clean)

# --- the sweep: no planted secret may survive anywhere -------------------------------------------------
for secret in samples.SECRETS:
    assert secret not in after, f"LEAK: {secret}"
assert json.dumps(doc) == before, "redact() must not modify its input"

# --- what is kept, and what it looks like ----------------------------------------------------------------
e0 = clean["log"]["entries"][0]
headers = {h["name"]: h["value"] for h in e0["request"]["headers"]}
print("masked request headers:", headers)
assert headers["Authorization"] == "Bearer <redacted:31>"
assert headers["Cookie"] == "sessionid=<redacted:23>; theme=<redacted:4>"
assert headers["X-Custom"] == "<redacted:57>"               # a JWT in an innocently named header: caught by SHAPE
e3 = clean["log"]["entries"][3]
assert e3["request"]["url"] == "https://example.com/api/data?api_key=<redacted:20>&page=2"
assert e3["request"]["queryString"] == [{"name": "api_key", "value": "<redacted:20>"}, {"name": "page", "value": "2"}]
assert json.loads(e3["response"]["content"]["text"]) == {"access_token": "<redacted:22>", "user": "bob"}
e4 = clean["log"]["entries"][4]
assert json.loads(e4["request"]["postData"]["text"]) == {"username": "bob", "password": "<redacted:19>"}

# everything that is not a secret is untouched: this is what makes the redacted file still useful
for a, b in zip(doc["log"]["entries"], clean["log"]["entries"]):
    assert a["timings"] == b["timings"] and a["time"] == b["time"] and a["startedDateTime"] == b["startedDateTime"]
    assert a["response"]["status"] == b["response"]["status"]

# --- idempotence: masking a masked file changes nothing --------------------------------------------------
assert redact(clean) == clean
assert mask_url(mask_url("https://u:pw@h/p?token=abc#access_token=zz")) == mask_url("https://u:pw@h/p?token=abc#access_token=zz")

# --- edge cases that bit real implementations ----------------------------------------------------------------
assert not sensitive(":authority") and not sensitive("Author") and not sensitive("access-control-allow-credentials")
assert sensitive("Authorization") and sensitive("X-CSRF-Token") and sensitive("client_secret") and sensitive("key")
assert mask_header("Set-Cookie", "id=abc123; Path=/; HttpOnly") == "id=<redacted:6>; Path=/; HttpOnly"
assert mask_url("https://h/cb#access_token=abc&state=1") == "https://h/cb#access_token=<redacted:3>&state=1"
assert mask_url("https://u:pw@h/") == "https://<redacted:4>@h/"
assert redact_body("user=bob&password=pw", "application/x-www-form-urlencoded") == "user=bob&password=<redacted:2>"
assert scrub_text("token: abc123 ok") == "token: <redacted:6> ok"
assert redact_body("not json {", "application/json") == "not json {"

print("module 04 ok")
