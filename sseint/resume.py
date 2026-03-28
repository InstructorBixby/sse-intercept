"""Did the reconnect resume, or start again?

The `id:` field and the `Last-Event-ID` request header are the
spec's resume mechanism, and the usual outcome of cutting a stream
in half is one of these:

1. the client reconnects with `Last-Event-ID` set to the last id it
   saw -- correct;
2. the client reconnects with no header, and the server starts from
   the beginning, so the user sees the first half twice;
3. the client reconnects with the header, and the server ignores it,
   which is the same outcome but a different owner;
4. the client does not reconnect at all and leaves a half-rendered
   message on screen with no error.

Telling those four apart by reading a transcript is tedious and easy
to get wrong, so it is a function. It takes recorded exchanges in
order and reports, per reconnect, what was claimed and what came back.
"""
from __future__ import annotations

from dataclasses import dataclass

from sseint.reassemble import reassemble


def last_id(frames) -> str | None:
    for f in reversed(frames):
        if f.id is not None:
            return f.id
    return None


def header(pairs, name: str) -> str | None:
    for k, v in pairs:
        if k.lower() == name.lower():
            return v
    return None


@dataclass
class Reconnect:
    after: int                  # exchange number that was cut
    exchange: int               # exchange number of the retry
    last_id_seen: str | None
    last_id_sent: str | None
    resumed: bool               # server continued rather than restarted
    overlap: int                # characters repeated from the first part

    def verdict(self) -> str:
        if self.last_id_sent is None:
            return ("client reconnected without Last-Event-ID; the "
                    "server has no way to resume and the first part "
                    "is repeated")
        if self.last_id_sent != self.last_id_seen:
            return (f"client sent Last-Event-ID {self.last_id_sent!r} "
                    f"but the last id it received was "
                    f"{self.last_id_seen!r}")
        if not self.resumed:
            return ("client sent the correct Last-Event-ID and the "
                    "server restarted anyway")
        return "resumed correctly"


def analyse(exchanges, same_path=True) -> list[Reconnect]:
    out = []
    for first, second in zip(exchanges, exchanges[1:]):
        if same_path and first.path != second.path:
            continue
        seen = last_id(first.frames)
        sent = header(second.request_headers, "last-event-id")
        a = reassemble(first.frames)
        b = reassemble(second.frames)
        overlap = _overlap(a, b)
        out.append(Reconnect(
            after=first.n, exchange=second.n, last_id_seen=seen,
            last_id_sent=sent, resumed=overlap == 0 and bool(b),
            overlap=overlap))
    return out


def _overlap(first: str, second: str) -> int:
    """How much of the first part the second part repeats."""
    if not first or not second:
        return 0
    limit = min(len(first), len(second))
    for n in range(limit, 0, -1):
        if second.startswith(first[:n]):
            return n
    return 0
