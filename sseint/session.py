"""Session files.

Append-only JSON lines. The format is chosen so that a session is
still readable after the process writing it was killed, which is how
most of them end -- `tail -f` on a run in progress is useful, and a
partial file is a valid session minus its last line.

Record types:

    meta      once per file: tool version, clock, start wall time
    exchange  one per request/response pair
    frame     one per decoded frame
    note      anything the proxy wants to say about an exchange
    end       one per exchange, with the frame count
    rotate    last record of a file: names the file that continues it

Rotation exists because a day pointed at a chatty client produced a
multi-gigabyte file that no editor would open and `read()` would have
loaded entirely into memory. At the size limit the writer emits a
`rotate` record naming the next file and continues there; `read()`
follows the chain by default, so a rotated session is still one
session.
"""
from __future__ import annotations

import base64
import json
import pathlib
import threading
import time

from sseint import __version__, redact
from sseint.frame import Frame

FORMAT = 3
DEFAULT_MAX_BYTES = 256 * 1024 * 1024


class SessionWriter:

    def __init__(self, path, clock=time.monotonic, now=time.time,
                 redact_headers: bool = True,
                 max_bytes: int | None = DEFAULT_MAX_BYTES):
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.redact_headers = redact_headers
        self.max_bytes = max_bytes
        self._lock = threading.Lock()
        self._clock = clock
        self._now = now
        self._part = 0
        self._written = 0
        self._fh = None
        self._open(self.path)

    # -- files ------------------------------------------------------
    def _open(self, path):
        self._current = pathlib.Path(path)
        self._fh = self._current.open("a", encoding="utf-8")
        self._written = self._current.stat().st_size
        meta = {"t": "meta", "format": FORMAT, "tool": "sse-intercept",
                "tool_version": __version__, "clock": "monotonic",
                "started_at": self._now(),
                "redacted": self.redact_headers}
        if self._part:
            meta["part"] = self._part
        if not self.redact_headers:
            meta["warning"] = ("headers are NOT redacted in this file; "
                               "it may contain credentials")
        self._emit(meta)

    def _rotate(self):
        self._part += 1
        nxt = self.path.with_name(f"{self.path.name}.{self._part}")
        self._emit({"t": "rotate", "next": nxt.name,
                    "part": self._part})
        self._fh.close()
        self._open(nxt)

    def _emit(self, obj):
        line = json.dumps(obj, ensure_ascii=False) + "\n"
        self._fh.write(line)
        self._fh.flush()
        self._written += len(line.encode("utf-8"))

    def _write(self, obj):
        with self._lock:
            self._emit(obj)
            if (self.max_bytes is not None
                    and self._written >= self.max_bytes):
                self._rotate()

    # -- records ----------------------------------------------------
    def _headers(self, pairs):
        pairs = list(pairs)
        if self.redact_headers:
            pairs = redact.headers(pairs)
        return [list(h) for h in pairs]

    def exchange(self, ex, request_headers=()):
        self._write({
            "t": "exchange", "ex": ex.n, "host": ex.host,
            "method": ex.method, "path": ex.path, "status": ex.status,
            "request_headers": self._headers(request_headers),
            "response_headers": self._headers(ex.headers),
            "decoder": ex.decoder,
        })

    def frame(self, ex, frame: Frame, added_ms: int = 0, ops=()):
        rec = {
            "t": "frame", "ex": ex.n, "seq": frame.seq,
            "at": round(frame.t, 6), "kind": frame.kind,
            "fields": [list(f) for f in frame.fields],
            "comments": list(frame.comments),
        }
        if frame.note:
            rec["note"] = frame.note
        if added_ms:
            rec["added_ms"] = added_ms
        if ops:
            rec["ops"] = list(ops)
        try:
            frame.raw.decode("utf-8")
        except UnicodeDecodeError:
            rec["raw_b64"] = base64.b64encode(frame.raw).decode("ascii")
        self._write(rec)

    def note(self, ex, text):
        self._write({"t": "note", "ex": ex.n, "text": text,
                     "at": round(self._clock(), 6)})

    def end(self, ex):
        self._write({"t": "end", "ex": ex.n, "frames": len(ex.frames),
                     "at": round(ex.frames[-1].t, 6) if ex.frames else 0.0})

    def close(self):
        with self._lock:
            if self._fh is not None:
                self._fh.close()
                self._fh = None


class Exchange:
    """A replayable exchange read back off disk."""

    def __init__(self, rec):
        self.n = rec["ex"]
        self.host = rec.get("host", "")
        self.method = rec.get("method", "GET")
        self.path = rec.get("path", "/")
        self.status = rec.get("status", "HTTP/1.1 200 OK")
        self.request_headers = [tuple(h) for h in
                                rec.get("request_headers", [])]
        self.headers = [tuple(h) for h in
                        rec.get("response_headers", [])]
        self.decoder = rec.get("decoder")
        self.frames: list[Frame] = []
        self.notes: list[str] = []
        self.added_ms: dict[int, int] = {}
        self.ops: dict[int, list[str]] = {}


def read(path, follow: bool = True) -> tuple[dict, list[Exchange]]:
    """Read a session, following rotation. A truncated last line is
    ignored rather than fatal."""
    meta: dict = {}
    order: list[Exchange] = []
    by_n: dict[int, Exchange] = {}
    current = pathlib.Path(path)
    seen: set[pathlib.Path] = set()
    while current is not None and current.resolve() not in seen:
        seen.add(current.resolve())
        nxt = None
        for line in current.read_text(
                encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            kind = rec.get("t")
            if kind == "meta":
                if not meta:
                    meta = rec
            elif kind == "rotate":
                nxt = current.with_name(rec["next"]) if follow else None
            elif kind == "exchange":
                ex = by_n.get(rec["ex"])
                if ex is None:
                    ex = Exchange(rec)
                    order.append(ex)
                    by_n[ex.n] = ex
            elif kind == "frame":
                ex = by_n.get(rec.get("ex"))
                if ex is None:
                    continue
                raw = rec.get("raw_b64")
                frame = Frame(
                    seq=rec["seq"], t=rec.get("at", 0.0),
                    kind=rec.get("kind", "event"),
                    raw=base64.b64decode(raw) if raw else b"",
                    fields=[tuple(f) for f in rec.get("fields", [])],
                    comments=list(rec.get("comments", [])),
                    note=rec.get("note"))
                ex.frames.append(frame)
                if rec.get("added_ms"):
                    ex.added_ms[frame.seq] = rec["added_ms"]
                if rec.get("ops"):
                    ex.ops[frame.seq] = list(rec["ops"])
            elif kind == "note":
                ex = by_n.get(rec.get("ex"))
                if ex is not None:
                    ex.notes.append(rec.get("text", ""))
        current = nxt if (nxt and nxt.exists()) else None
    return meta, order
