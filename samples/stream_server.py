"""A local SSE server with switchable misbehaviour.

Every quirk here was copied from a real endpoint. Having them in one
place means a decoder change can be checked against all of them in a
second, instead of waiting for the next engagement to find out.

    python samples/stream_server.py --port 9000 --quirk no-final-blank

Quirks:

    none            well-behaved: LF separators, [DONE], blank line
    crlf            CRLF between fields and LF for the separator
    no-final-blank  last frame has no trailing blank line
    split-separator the blank line arrives in two writes
    keepalive       a `:` comment every 200ms alongside tokens
    gzip            gzip with a sync flush per frame
    gzip-unlabelled gzip body with the Content-Encoding header removed
    no-sentinel     ends without [DONE]
    stall           a 6-second gap in the middle
    content-length  declares a Content-Length on a streaming response
    huge-frame      one frame of 200kB, to exercise buffering
"""
from __future__ import annotations

import argparse
import http.server
import json
import time
import zlib

TOKENS = ["The ", "quick ", "brown ", "fox ", "jumps ", "over ",
          "the ", "lazy ", "dog", "."]


def frames(quirk):
    sep = "\r\n" if quirk == "crlf" else "\n"
    for i, tok in enumerate(TOKENS):
        payload = json.dumps(
            {"choices": [{"delta": {"content": tok}}]})
        yield f"event: token{sep}data: {payload}{sep}\n", 0.05
        if quirk == "keepalive" and i % 3 == 2:
            yield ": keep-alive\n\n", 0.2
        if quirk == "stall" and i == 4:
            yield "", 6.0
    if quirk == "huge-frame":
        yield "data: " + "x" * 200_000 + "\n\n", 0.05
    if quirk != "no-sentinel":
        tail = "data: [DONE]\n" if quirk == "no-final-blank" \
            else "data: [DONE]\n\n"
        yield tail, 0.0


class Handler(http.server.BaseHTTPRequestHandler):

    protocol_version = "HTTP/1.1"
    quirk = "none"

    def do_GET(self):
        self._stream()

    def do_POST(self):
        length = int(self.headers.get("content-length") or 0)
        if length:
            self.rfile.read(length)
        self._stream()

    def _stream(self):
        body = list(frames(self.quirk))
        gzipping = self.quirk in ("gzip", "gzip-unlabelled")
        self.send_response(200)
        self.send_header("content-type", "text/event-stream")
        self.send_header("cache-control", "no-cache")
        if gzipping and self.quirk == "gzip":
            self.send_header("content-encoding", "gzip")
        if self.quirk == "content-length":
            self.send_header("content-length",
                             str(sum(len(t) for t, _ in body)))
        self.send_header("connection", "close")
        self.end_headers()

        co = (zlib.compressobj(wbits=16 + zlib.MAX_WBITS)
              if gzipping else None)
        for text, wait in body:
            raw = text.encode()
            if co is not None:
                raw = co.compress(raw) + co.flush(zlib.Z_SYNC_FLUSH)
            if self.quirk == "split-separator" and raw.endswith(b"\n\n"):
                self._write(raw[:-1])
                time.sleep(0.01)
                self._write(raw[-1:])
            else:
                self._write(raw)
            if wait:
                time.sleep(wait)
        if co is not None:
            self._write(co.flush())

    def _write(self, raw: bytes):
        try:
            self.wfile.write(raw)
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, fmt, *args):
        pass


def serve(port=9000, quirk="none", host="127.0.0.1"):
    handler = type("Q", (Handler,), {"quirk": quirk})
    return http.server.ThreadingHTTPServer((host, port), handler)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=9000)
    ap.add_argument("--quirk", default="none")
    args = ap.parse_args()
    srv = serve(args.port, args.quirk, args.host)
    print(f"sample SSE server on http://{args.host}:{srv.server_address[1]}"
          f"/stream  quirk={args.quirk}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
