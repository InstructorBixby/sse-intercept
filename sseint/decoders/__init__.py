"""Stream decoders, chosen by content type.

A decoder is fed bytes and returns whole frames. It must never block,
never assume a read lands on a frame boundary, and never swallow bytes
it cannot parse -- an undecodable chunk comes back as a frame with a
note so the view still shows something.
"""
from __future__ import annotations

from sseint.decoders.chunked import ChunkedDecoder
from sseint.decoders.ndjson import NDJSONDecoder
from sseint.decoders.sse import SSEDecoder

REGISTRY = [SSEDecoder, NDJSONDecoder, ChunkedDecoder]
BY_NAME = {cls.name: cls for cls in REGISTRY}


def for_content_type(ctype: str | None):
    base = (ctype or "").split(";")[0].strip().lower()
    for cls in REGISTRY:
        if base in cls.content_types:
            return cls()
    return None


def by_name(name: str):
    cls = BY_NAME.get(name)
    return cls() if cls else None
