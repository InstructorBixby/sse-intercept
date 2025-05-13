"""The streaming relay, with rules in the path.

Rules force an uncomfortable trade. Without them the relay forwards
each chunk before decoding it, so the proxy adds no measurable
latency. With them it cannot: deciding whether to drop frame 12
requires having parsed frame 12, which means the bytes wait.

Resolution: two paths.

- **No engine, or an engine whose rules cannot match this exchange**
  (host and path are known before the first byte, so most rule sets
  are excluded here): forward the chunk, then decode a copy. Zero
  added latency, and this is the path a plain observation run takes.
- **Engine armed**: hold the chunk, decode, plan, write what the plan
  says. The relay then records `added_ms` per frame, so the timing in
  the session says how much of the gap was the proxy. An instrument
  that does not report its own overhead is not an instrument.
"""
from __future__ import annotations

import time

from sseint.apply import plan
from sseint.rules import Context


class Relay:

    def __init__(self, decoder, inflater, tap, exchange, engine=None,
                 ctx: Context | None = None, pause_budget_s: float = 30.0,
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
        self._reported_encoding = False

    @property
    def intercepting(self) -> bool:
        return bool(self.engine) and self.decoder is not None

    def chunk(self, chunk: bytes, wfile) -> bool:
        """Handle one chunk. Returns False once the stream is over."""
        if self._cut:
            return False
        if not self.intercepting:
            wfile.write(chunk)
            wfile.flush()
            self._observe(chunk)
            return True
        return self._intercept(chunk, wfile)

    def finish(self, wfile):
        if self.decoder is None or self._cut:
            return
        tail = self.inflater.close()
        frames = []
        if tail:
            frames += self.decoder.feed(tail)
        frames += self.decoder.close()
        for frame in frames:
            if self.intercepting:
                self._emit(frame, wfile)
            else:
                self.tap.frame(self.ex, frame)

    # -- observation only -------------------------------------------
    def _observe(self, chunk: bytes):
        if self.decoder is None:
            return
        body = self.inflater.feed(chunk)
        self._encoding_note()
        for frame in self.decoder.feed(body):
            self.tap.frame(self.ex, frame)

    # -- intercepting -----------------------------------------------
    def _intercept(self, chunk: bytes, wfile) -> bool:
        body = self.inflater.feed(chunk)
        self._encoding_note()
        for frame in self.decoder.feed(body):
            if not self._emit(frame, wfile):
                return False
        return True

    def _emit(self, frame, wfile) -> bool:
        ops, fired = self.engine.decide(frame, self.ctx)
        p = plan(frame, ops)
        t0 = self._clock()
        if p.delay_ms:
            self._sleep(p.delay_ms / 1000.0)
        if p.pause:
            self._hold()
        for note in p.notes:
            self.tap.note(self.ex, f"{frame.seq}: {note}")
        for blob in p.emit:
            wfile.write(blob)
        wfile.flush()
        frame.note = frame.note or (",".join(fired) or None)
        self.tap.frame(self.ex, frame,
                       added_ms=int((self._clock() - t0) * 1000),
                       ops=fired, emitted=len(p.emit))
        if p.cut:
            self._cut = True
            return False
        return True

    def _hold(self):
        """Hold the stream, but not forever.

        A pause with no release looks like a hung server to the client,
        and the client's read timeout fires -- which is a different
        test from the one that was intended, and worse, it looks like
        the pause worked. So a pause is bounded and says when it ended
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
                f"releasing. Whatever the client did after this is "
                f"the proxy's fault, not the server's.")
            self.tap.paused = False
