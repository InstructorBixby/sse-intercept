"""Transfer-Encoding: chunked, as a decoder of last resort.

Plenty of streaming endpoints send `application/json` or
`text/plain` with chunked encoding and no framing convention at all.
There is still something to see: the chunk boundaries the server chose
are a frame structure, because they are what the client's read loop
observes.

So this decoder emits one frame per HTTP chunk. It is only correct if
the relay has not already de-chunked the body, which is why the proxy
passes the wire bytes and not the decoded body.
"""
from __future__ import annotations

import time

from sseint.frame import Frame


class ChunkedDecoder:

    name = "chunked"
    # Chosen explicitly with --decoder, never by content type: these
    # types are overwhelmingly not streams and guessing would put a
    # frame view on every JSON response in the session.
    content_types = ()

    def __init__(self, clock=None):
        self._buf = b""
        self._seq = 0
        self._clock = clock or time.monotonic
        self._t0 = None
        self._done = False

    def feed(self, chunk: bytes) -> list[Frame]:
        if self._t0 is None:
            self._t0 = self._clock()
        self._buf += chunk
        out = []
        while not self._done:
            frame = self._next()
            if frame is None:
                break
            out.append(frame)
        return out

    def close(self) -> list[Frame]:
        if self._buf.strip() and not self._done:
            raw, self._buf = self._buf, b""
            self._seq += 1
            return [Frame(seq=self._seq, t=self._clock() - self._t0,
                          kind="chunk", raw=raw,
                          fields=[("data", _text(raw))],
                          note="truncated")]
        return []

    def _next(self) -> Frame | None:
        if b"\r\n" not in self._buf:
            return None
        line, rest = self._buf.split(b"\r\n", 1)
        size_part = line.split(b";", 1)[0].strip()
        try:
            size = int(size_part, 16)
        except ValueError:
            # Not chunked after all. Hand the caller what arrived
            # rather than silently producing nothing.
            raw, self._buf = self._buf, b""
            self._seq += 1
            return Frame(seq=self._seq, t=self._clock() - self._t0,
                         kind="chunk", raw=raw,
                         fields=[("data", _text(raw))],
                         note="not-chunked")
        if size == 0:
            self._done = True
            self._buf = b""
            self._seq += 1
            return Frame(seq=self._seq, t=self._clock() - self._t0,
                         kind="chunk", raw=b"", fields=[],
                         note="last-chunk")
        if len(rest) < size + 2:
            return None
        body, self._buf = rest[:size], rest[size + 2:]
        self._seq += 1
        return Frame(seq=self._seq, t=self._clock() - self._t0,
                     kind="chunk", raw=body,
                     fields=[("data", _text(body))])


def _text(raw: bytes) -> str:
    return raw.decode("utf-8", "replace")
