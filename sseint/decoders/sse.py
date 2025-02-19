"""text/event-stream framing.

Splitting the byte stream on b"\n\n" is wrong twice over. A frame
separator is any of CRLF CRLF, LF LF or CR CR, and servers mix them --
one endpoint here sends CRLF between fields and LF for the blank line.
A comment line (one starting with ":") is not a frame at all; it is a
keep-alive, and treating it as a boundary cuts real frames in half.

And a read is not a frame. Nothing guarantees a chunk ends on a
boundary; in practice a slow token stream delivers one frame per
segment and then, once per run, delivers a separator split down the
middle. The buffer tail is therefore kept, never scanned and dropped.
"""
from __future__ import annotations

import re
import time

from sseint.frame import Frame

SEPARATORS = (b"\r\n\r\n", b"\n\n", b"\r\r")
LINE_SPLIT = re.compile(r"\r\n|\n|\r")
PARTIAL = max(len(s) for s in SEPARATORS) - 1

# Not in the spec: a convention several streaming chat APIs share. A
# final frame whose data is the literal "[DONE]". Worth recognising
# because its absence is a finding -- a client that keys completion
# off it and never receives it is a client that hangs.
DONE_SENTINEL = "[DONE]"


class SSEDecoder:

    name = "sse"
    content_types = ("text/event-stream",)

    def __init__(self, clock=None):
        self._buf = b""
        self._seq = 0
        self._clock = clock or time.monotonic
        self._t0 = None

    # -- feeding ----------------------------------------------------
    def feed(self, chunk: bytes) -> list[Frame]:
        if self._t0 is None:
            self._t0 = self._clock()
        self._buf += chunk
        out = []
        while True:
            block, rest = self._split(self._buf)
            if block is None:
                break
            self._buf = rest
            out.append(self._frame(block))
        return out

    def close(self) -> list[Frame]:
        """Flush the tail.

        A server that ends the response without a trailing blank line
        has still sent a frame. Dropping it loses the last token of
        every such stream, which is exactly the frame a report wants.
        """
        if not self._buf.strip():
            self._buf = b""
            return []
        block, self._buf = self._buf, b""
        f = self._frame(block)
        f.note = "eof"
        return [f]

    @property
    def waiting_on_boundary(self) -> bool:
        """Buffer tail might be half a separator, not a stall."""
        tail = self._buf[-PARTIAL:]
        return bool(tail) and any(s.startswith(tail) for s in SEPARATORS)

    # -- parsing ----------------------------------------------------
    @staticmethod
    def _split(buf: bytes):
        best = None
        for sep in SEPARATORS:
            i = buf.find(sep)
            if i != -1 and (best is None or i < best[0]):
                best = (i, len(sep))
        if best is None:
            return None, buf
        i, n = best
        return buf[:i], buf[i + n:]

    def _frame(self, block: bytes) -> Frame:
        text = block.decode("utf-8", "replace")
        fields: list[tuple[str, str]] = []
        comments: list[str] = []
        for line in LINE_SPLIT.split(text):
            if not line:
                continue
            if line.startswith(":"):
                comments.append(line[1:])
                continue
            name, sep, value = line.partition(":")
            if not sep:
                fields.append((line, ""))
                continue
            if value.startswith(" "):
                value = value[1:]
            fields.append((name, value))
        self._seq += 1
        return Frame(
            seq=self._seq,
            t=self._clock() - self._t0,
            kind="event" if fields else "comment",
            raw=block,
            fields=fields,
            comments=comments,
        )


def retry_of(frame: Frame) -> int | None:
    raw = frame.first("retry")
    if raw is None:
        return None
    try:
        return int(raw.strip())
    except ValueError:
        return None


def is_done(frame: Frame) -> bool:
    return frame.data.strip() == DONE_SENTINEL
