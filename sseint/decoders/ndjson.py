"""NDJSON / JSON-lines.

Simpler than SSE and wrong in a different way: the frame boundary is a
newline, which means a newline inside a JSON string is not a boundary.
JSON requires string newlines to be escaped, so splitting on a raw
newline is in fact safe for well-formed input -- but input here is not
assumed well-formed, so each line is parsed, and a line that does not
parse is held and retried with the next one.

Holding has to be bounded. A server emitting a stream of lines that
are each individually invalid JSON -- a plain-text error log with the
NDJSON content type still on it -- would otherwise accumulate the
whole response in the hold buffer and show nothing. At the cap the
held text is surrendered as one `unparsed` frame and holding restarts.
"""
from __future__ import annotations

import json
import time

from sseint.frame import Frame

MAX_HELD_BYTES = 1024 * 1024


class NDJSONDecoder:

    name = "ndjson"
    content_types = ("application/x-ndjson", "application/jsonl",
                     "application/x-jsonlines", "application/json-seq")

    def __init__(self, clock=None, max_held_bytes=MAX_HELD_BYTES):
        self._buf = b""
        self._held = ""
        self._seq = 0
        self._clock = clock or time.monotonic
        self._t0 = None
        self.max_held_bytes = max_held_bytes

    def feed(self, chunk: bytes) -> list[Frame]:
        if self._t0 is None:
            self._t0 = self._clock()
        self._buf += chunk
        out = []
        while b"\n" in self._buf:
            line, self._buf = self._buf.split(b"\n", 1)
            frame = self._line(line)
            if frame is not None:
                out.append(frame)
            if len(self._held) > self.max_held_bytes:
                out.append(self._surrender())
        return out

    def close(self) -> list[Frame]:
        rest, self._buf = self._buf, b""
        frames = []
        if rest.strip():
            f = self._line(rest, final=True)
            if f is not None:
                f.note = "eof"
                frames.append(f)
        if self._held:
            frames.append(self._surrender())
        return frames

    def _surrender(self) -> Frame:
        text, self._held = self._held, ""
        return self._emit(text.encode(), "unparsed")

    def _line(self, raw: bytes, final: bool = False) -> Frame | None:
        text = self._held + raw.decode("utf-8", "replace")
        if not text.strip():
            return None
        try:
            json.loads(text)
        except ValueError:
            if not final:
                # Hold it: an unterminated object means the newline we
                # split on was inside a string, or the server is
                # pretty-printing into a stream, which one of them does.
                self._held = text + "\n"
                return None
            return self._emit(text.encode(), "unparsed")
        self._held = ""
        return self._emit(text.encode(), None)

    def _emit(self, raw: bytes, note: str | None) -> Frame:
        self._seq += 1
        return Frame(seq=self._seq, t=self._clock() - self._t0,
                     kind="line", raw=raw,
                     fields=[("data", raw.decode("utf-8", "replace"))],
                     note=note)
