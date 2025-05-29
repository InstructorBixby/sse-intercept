"""Where decoded frames go.

The proxy does not print. It hands events to a tap, and the tap
decides whether they become terminal output, a session file, or both.
"""
from __future__ import annotations

import itertools
import sys
import threading
from dataclasses import dataclass, field

from sseint.frame import Frame


@dataclass
class Exchange:
    n: int
    host: str
    method: str
    path: str
    status: str
    headers: list[tuple[str, str]]
    decoder: str | None
    frames: list[Frame] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


class ConsoleTap:

    def __init__(self, stream=sys.stderr, quiet=False):
        self.stream = stream
        self.quiet = quiet
        self.paused = False
        self._ids = itertools.count(1)
        self._lock = threading.Lock()

    def _say(self, text):
        with self._lock:
            print(text, file=self.stream, flush=True)

    def exchange(self, *, host, method, path, status, headers, decoder):
        ex = Exchange(n=next(self._ids), host=host, method=method,
                      path=path, status=status, headers=headers,
                      decoder=decoder)
        self._say(f"[{ex.n}] {method} https://{host}{path} -> {status}"
                  f"  decoder={decoder or '-'}")
        return ex

    def frame(self, ex, frame: Frame, added_ms: int = 0, ops=(),
              emitted: int = 1):
        ex.frames.append(frame)
        if self.quiet:
            return
        mark = {"comment": ":", "event": "#"}.get(frame.kind, "~")
        bits = []
        if ops:
            bits.append("+".join(ops))
        if added_ms:
            bits.append(f"+{added_ms}ms by proxy")
        if emitted != 1:
            bits.append(f"{emitted} frame(s) written")
        if frame.note and frame.note not in ops:
            bits.append(frame.note)
        tail = f"   [{'; '.join(bits)}]" if bits else ""
        self._say(f"[{ex.n}] {mark}{frame.seq:<4} +{frame.t:7.3f}s  "
                  f"{frame.summary()}{tail}")

    def note(self, ex, text):
        ex.notes.append(text)
        self._say(f"[{ex.n}] ! {text}")

    def end(self, ex):
        self._say(f"[{ex.n}] end, {len(ex.frames)} frame(s)")

    def refused(self, host):
        self._say(f"refused {host}: not in scope")

    def handshake_failed(self, host, why):
        self._say(f"handshake with {host} failed: {why}")
