"""Content-Encoding on a stream.

A gzipped `text/event-stream` is a real thing and it breaks the naive
path completely: `gzip.decompress` wants the whole member, so a
decoder fed raw deflate bytes produces nothing for the entire stream
and then everything at once. The frame view goes blank and the timing
numbers become a lie, which is worse than no numbers.

`zlib.decompressobj` handles it: feed it each chunk and take whatever
falls out. A server that flushes per frame (Z_SYNC_FLUSH) gives back a
frame per chunk; one that does not gives back frames in bursts, and
that burstiness is itself worth seeing, so the timing recorded is the
arrival time of the compressed chunk, not of the inflated bytes.

The other case, which cost an afternoon: an upstream proxy that strips
`Content-Encoding: gzip` from the response headers and forwards the
body still compressed. Header-driven dispatch then hands deflate bytes
to the SSE decoder, which dutifully reports one enormous unparseable
frame. So the encoding is sniffed from the first bytes as well as read
from the header, and a disagreement between the two is reported --
it is a finding about the path, not an inconvenience.
"""
from __future__ import annotations

import zlib

GZIP_MAGIC = b"\x1f\x8b"
ZLIB_FIRST = {0x78}


def sniff(prefix: bytes) -> str | None:
    if prefix.startswith(GZIP_MAGIC):
        return "gzip"
    if len(prefix) >= 2 and prefix[0] in ZLIB_FIRST:
        if (prefix[0] * 256 + prefix[1]) % 31 == 0:
            return "deflate"
    return None


class Inflater:
    """Incremental decoder for one response body."""

    def __init__(self, encoding: str | None):
        self.encoding = (encoding or "").lower().strip()
        self.declared = self.encoding
        self.observed: str | None = None
        self._obj = None
        self._started = False

    @property
    def mismatch(self) -> str | None:
        if self.observed and self.observed != self.declared:
            if not self.declared:
                return (f"body looks like {self.observed} but no "
                        f"Content-Encoding header was sent")
            return (f"Content-Encoding says {self.declared!r} but the "
                    f"body looks like {self.observed}")
        return None

    def feed(self, chunk: bytes) -> bytes:
        if not self._started:
            self._started = True
            self.observed = sniff(chunk[:4])
            enc = self.declared or self.observed or ""
            if enc == "gzip":
                self._obj = zlib.decompressobj(16 + zlib.MAX_WBITS)
            elif enc == "deflate":
                self._obj = zlib.decompressobj()
            elif enc in ("", "identity"):
                self._obj = None
            else:
                # br, zstd: not handled, and saying so beats
                # pretending the bytes are text.
                self._obj = None
                self.observed = enc
        if self._obj is None:
            return chunk
        try:
            return self._obj.decompress(chunk)
        except zlib.error:
            # Give up on decoding, not on relaying. The proxy has
            # already forwarded these bytes; only the view suffers.
            self._obj = None
            return b""

    def close(self) -> bytes:
        if self._obj is None:
            return b""
        try:
            return self._obj.flush()
        except zlib.error:
            return b""
