"""Export a session as HAR.

HAR has no concept of a stream. `response.content.text` is one string
and `timings` describes one request, so a faithful export is
impossible and a lossy one is still useful: it gets a session into
every tool that reads HAR, and those tools are where the rest of a
report gets written.

What is done about the loss:

- `response.content.text` is the reassembled message, which is what a
  HAR consumer expects a body to be.
- `timings.wait` is time to first frame, the only honest mapping: it
  is the interval the client spent waiting before anything arrived.
- every frame, with its relative time, goes in `_frames` on the entry.
  A leading underscore is HAR's own convention for a custom field, so
  a reader that does not know about it ignores it.
- `_sseint` on the log records that the body was reassembled and by
  which mode, so nobody quotes `content.text` as if it arrived that
  way.
"""
from __future__ import annotations

import datetime as dt
import re

from sseint import __version__
from sseint.reassemble import reassemble
from sseint.timing import analyse

HAR_VERSION = "1.2"
# The status recorded for an exchange is whatever the proxy had: an
# HTTP/1.1 status line, or just "200 OK" over h2 where there is no
# status line at all. Both have to yield 200.
STATUS_RE = re.compile(r"\b([1-5]\d{2})\b")


def _headers(pairs):
    return [{"name": k, "value": v} for k, v in pairs]


def _started(meta, offset: float) -> str:
    base = meta.get("started_at")
    if not base:
        return ""
    when = dt.datetime.fromtimestamp(base + offset, dt.timezone.utc)
    return when.isoformat(timespec="milliseconds").replace(
        "+00:00", "Z")


def entry(meta, ex, mode="data") -> dict:
    st = analyse(ex.frames, added=ex.added_ms)
    body = reassemble(ex.frames, mode)
    total_ms = int((st.total_s or 0) * 1000)
    wait_ms = int((st.first_frame_s or 0) * 1000)
    return {
        "startedDateTime": _started(meta, 0.0),
        "time": total_ms,
        "request": {
            "method": ex.method,
            "url": f"https://{ex.host}{ex.path}",
            "httpVersion": "",
            "headers": _headers(ex.request_headers),
            "queryString": [],
            "cookies": [],
            "headersSize": -1,
            "bodySize": -1,
        },
        "response": {
            "status": status_code(ex.status),
            "statusText": ex.status,
            "httpVersion": "",
            "headers": _headers(ex.headers),
            "cookies": [],
            "content": {
                "size": len(body.encode("utf-8")),
                "mimeType": _mime(ex.headers),
                "text": body,
            },
            "redirectURL": "",
            "headersSize": -1,
            "bodySize": -1,
        },
        "cache": {},
        "timings": {"send": 0, "wait": wait_ms,
                    "receive": max(0, total_ms - wait_ms)},
        "_frames": [
            {
                "seq": f.seq,
                "at": round(f.t, 6),
                "kind": f.kind,
                "fields": [list(x) for x in f.fields],
                "comments": list(f.comments),
                "note": f.note,
                "added_ms": ex.added_ms.get(f.seq, 0),
                "ops": ex.ops.get(f.seq, []),
            }
            for f in ex.frames
        ],
        "_notes": list(ex.notes),
    }


def har(meta, exchanges, mode="data") -> dict:
    return {
        "log": {
            "version": HAR_VERSION,
            "creator": {"name": "sse-intercept",
                        "version": __version__},
            "entries": [entry(meta, ex, mode) for ex in exchanges],
            "_sseint": {
                "note": "response.content.text is REASSEMBLED from a "
                        "stream and did not arrive as one body. The "
                        "frames, with relative arrival times, are in "
                        "_frames on each entry.",
                "reassemble_mode": mode,
                "session_format": meta.get("format"),
            },
        },
    }


def status_code(status: str) -> int:
    m = STATUS_RE.search(status or "")
    return int(m.group(1)) if m else 0


def _mime(headers) -> str:
    for k, v in headers:
        if k.lower() == "content-type":
            return v
    return ""
