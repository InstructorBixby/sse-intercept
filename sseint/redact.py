"""Keep credentials out of session files.

A session file is evidence: it gets attached to a report, copied into
a ticket, and sometimes handed to whoever owns the service. It should
not contain a bearer token.

Default-on, because the one time it matters is the one time somebody
forgot the flag. `--no-redact` exists for a deliberate local
reproduction, and the session records that it was used, so a file with
secrets in it says so.

This is header-level only and makes no attempt to find secrets inside
frame bodies. Something that works on a transcript as a whole, with a
reversible mapping, is a different tool -- scrubkit does that, and
pointing a half-measure at the same problem would make both less
trustworthy.
"""
from __future__ import annotations

SENSITIVE = {
    "authorization", "proxy-authorization", "cookie", "set-cookie",
    "x-api-key", "api-key", "x-auth-token", "x-amz-security-token",
    "openai-organization",
}
KEEP_PREFIX = 4


def header_value(name: str, value: str) -> str:
    if name.lower() not in SENSITIVE:
        return value
    if not value:
        return value
    scheme, sep, rest = value.partition(" ")
    if sep and scheme.lower() in ("bearer", "basic", "digest", "token"):
        return f"{scheme} <redacted:{len(rest)}>"
    # Keep a short prefix: it is enough to tell two keys apart across
    # exchanges, which is sometimes the finding, and far too little to
    # use.
    head = value[:KEEP_PREFIX]
    return f"{head}<redacted:{max(0, len(value) - KEEP_PREFIX)}>"


def headers(pairs) -> list[tuple[str, str]]:
    return [(k, header_value(k, v)) for k, v in pairs]
