"""Replay a recorded stream to a client.

This is the feature that turns a session into a reproducer. A client
bug that needs a particular frame to arrive 4.2 seconds late, after a
keep-alive and before the sentinel, is not reproducible by asking the
real server nicely. It is reproducible by replaying the exact frames
with the exact gaps, as many times as it takes to attach a debugger.

Modes:

- `original`: sleep the recorded gap between frames.
- `fast`: no gaps at all, for checking a parser rather than a timeout.
- a multiplier: `--speed 4` divides every gap by four, which keeps the
  *shape* of the stream while making a 90-second transcript usable.

Gaps are taken from the recorded `at` values and each sleep is
computed against the replay's own start, so a slow write does not
accumulate drift across three hundred frames.

Every field is replayed, `id:` and `retry:` included. They were being
dropped by the header filter, which quietly broke the resume test:
a client replayed against a stream with no ids has nothing to put in
`Last-Event-ID`, so it looked like a client defect every time.
"""
from __future__ import annotations

import http.server
import threading
import time

from sseint.wire import encode

# Dropped from the replayed response head: the body is produced here,
# so the recorded framing and encoding headers would describe a
# different body than the one being sent.
DROP_HEADERS = {"content-length", "transfer-encoding",
                "content-encoding"}


class ReplayError(Exception):
    pass


def gaps(frames, speed: float = 1.0):
    """Yield (frame, seconds_to_wait_before_sending_it)."""
    if speed <= 0:
        raise ReplayError("speed must be positive")
    prev = 0.0
    for f in frames:
        yield f, max(0.0, (f.t - prev) / speed)
        prev = f.t


def write_stream(frames, wfile, speed=1.0, sleep=time.sleep,
                 clock=time.monotonic, on_frame=None):
    """Write frames to a file object, pacing against one start time."""
    start = clock()
    target = 0.0
    for frame, wait in gaps(frames, speed):
        target += wait
        drift = target - (clock() - start)
        if drift > 0:
            sleep(drift)
        wfile.write(encode(frame))
        wfile.flush()
        if on_frame is not None:
            on_frame(frame)


def make_handler(exchange, speed, on_frame=None):

    class Handler(http.server.BaseHTTPRequestHandler):

        protocol_version = "HTTP/1.1"

        def do_GET(self):
            self._serve()

        def do_POST(self):
            length = int(self.headers.get("content-length") or 0)
            if length:
                self.rfile.read(length)
            self._serve()

        def _serve(self):
            self.send_response(200)
            for k, v in exchange.headers:
                if k.lower() in DROP_HEADERS:
                    continue
                self.send_header(k, v)
            self.send_header("connection", "close")
            self.end_headers()
            try:
                write_stream(exchange.frames, self.wfile, speed,
                             on_frame=on_frame)
            except (BrokenPipeError, ConnectionResetError):
                # The client under test hanging up mid-stream is
                # frequently the result being looked for.
                pass

        def log_message(self, fmt, *args):
            pass

    return Handler


class ReplayServer:

    def __init__(self, exchange, addr=("127.0.0.1", 0), speed=1.0,
                 on_frame=None):
        self.exchange = exchange
        handler = make_handler(exchange, speed, on_frame)
        self.httpd = http.server.ThreadingHTTPServer(addr, handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever,
                                       daemon=True)

    @property
    def port(self) -> int:
        return self.httpd.server_address[1]

    def start(self):
        self.thread.start()

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.stop()
