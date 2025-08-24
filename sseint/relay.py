"""The streaming relay, with rules in the path.

`feed(chunk) -> bytes`. The relay decides what should go to the client
and returns it; it never touches a socket. That is what lets the same
code sit behind a mitmproxy stream hook and behind a test that feeds it
a bytestring.

Rules force an uncomfortable trade. Without them the relay can hand
back each chunk untouched and decode a copy, so nothing is added to
the path. With them it cannot: deciding whether to drop frame 12
requires having parsed frame 12.

Resolution: two paths.

- **No engine**: return the chunk as it arrived, decode a copy. This
  is the path an observation run takes and it adds nothing.
- **Engine armed**: decode, plan, return what the plan says. Every
  frame then records `added_ms`, so the timing in the session says how
  much of each gap was the proxy. An instrument that does not report
  its own overhead is not an instrument.
"""
from __future__ import annotations

import time

from sseint.apply import plan
from sseint.rules import Context


class Relay:

    def __init__(self, decoder, inflater, tap, exchange, engine=None,
                 ctx: Context | None = None,
                 pause_budget_s: float = 30.0,
                 sleep=time.sleep, clock=time.monotonic):
        self.decoder = decoder
        self.inflater = inflater
        self.tap = tap
        self.ex = exchange
        self.engine = engine
        self.ctx = ctx or Context()
        self.pause_budget_s = pause_budget_s
        self._sleep = sleep
        self._clock = clock
        self._cut = False

    @property
    def intercepting(self) -> bool:
        return bool(self.engine) and self.decoder is not None

    # -- the hook ---------------------------------------------------
    def feed(self, chunk: bytes) -> bytes:
        if self._cut:
            return b""
        if not self.intercepting:
            self._observe(chunk)
            return chunk
        out = b""
        for frame in self._decode(chunk):
            blob, keep = self._handle(frame)
            out += blob
            if not keep:
                self._cut = True
                break
        return out

    def finish(self) -> bytes:
        if self.decoder is None or self._cut:
            return b""
        frames = []
        tail = self.inflater.close()
        if tail:
            frames += self.decoder.feed(tail)
        frames += self.decoder.close()
        if not self.intercepting:
            for frame in frames:
                self.tap.frame(self.ex, frame)
            return b""
        out = b""
        for frame in frames:
            blob, keep = self._handle(frame)
            out += blob
            if not keep:
                break
        return out

    # -- internals --------------------------------------------------
    def _decode(self, chunk: bytes):
        body = self.inflater.feed(chunk)
        self._encoding_note()
        return self.decoder.feed(body)

    def _observe(self, chunk: bytes):
        if self.decoder is None:
            return
        for frame in self._decode(chunk):
            self.tap.frame(self.ex, frame)

    def _encoding_note(self):
        mismatch = self.inflater.mismatch
        if mismatch and not getattr(self, "_said_encoding", False):
            self._said_encoding = True
            self.tap.note(self.ex, mismatch)

    def _handle(self, frame) -> tuple[bytes, bool]:
        ops, fired = self.engine.decide(frame, self.ctx)
        p = plan(frame, ops)
        t0 = self._clock()
        if p.delay_ms:
            self._sleep(p.delay_ms / 1000.0)
        if p.pause:
            self._hold()
        for note in p.notes:
            self.tap.note(self.ex, f"frame {frame.seq}: {note}")
        frame.note = frame.note or (",".join(fired) or None)
        self.tap.frame(self.ex, frame,
                       added_ms=int((self._clock() - t0) * 1000),
                       ops=fired, emitted=len(p.emit))
        return b"".join(p.emit), not p.cut

    def _hold(self):
        """Hold the stream, but not forever.

        A pause with no release looks like a hung server, the client's
        read timeout fires, and the result looks like the pause
        worked. So a pause is bounded and says when it released
        itself.
        """
        self.tap.note(self.ex, "paused")
        deadline = self._clock() + self.pause_budget_s
        while self.tap.paused and self._clock() < deadline:
            self._sleep(0.05)
        if self.tap.paused:
            self.tap.note(
                self.ex,
                f"pause budget of {self.pause_budget_s:g}s expired, "
                f"releasing. Whatever the client does after this is "
                f"the proxy's doing, not the server's.")
            self.tap.paused = False
