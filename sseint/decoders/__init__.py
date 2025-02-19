"""Stream decoders, chosen by content type.

A decoder is fed bytes and returns whole frames. It must never block,
never assume a read lands on a frame boundary, and never swallow bytes
it cannot parse -- an undecodable chunk comes back as a `chunk` frame
so the view still shows something.
"""
from __future__ import annotations

from sseint.decoders.sse import SSEDecoder

REGISTRY = [SSEDecoder]


def for_content_type(ctype: str | None):
    base = (ctype or "").split(";")[0].strip().lower()
    for cls in REGISTRY:
        if base in cls.content_types:
            return cls()
    return None
