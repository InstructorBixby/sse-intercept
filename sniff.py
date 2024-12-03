"""Forward HTTP and print SSE frames as they arrive."""
import argparse
import socket
import socketserver
import sys
import time
from urllib.parse import urlsplit

import sseframe


def read_head(rfile):
    buf = b""
    while b"\r\n\r\n" not in buf:
        b = rfile.read(1)
        if not b:
            return None
        buf += b
    return buf


def parse_head(head):
    lines = head.decode("latin-1").split("\r\n")
    headers = []
    for line in lines[1:]:
        if not line:
            continue
        name, _, value = line.partition(":")
        headers.append((name.strip(), value.strip()))
    return lines[0], headers


def header(headers, name):
    for k, v in headers:
        if k.lower() == name.lower():
            return v
    return None


class Handler(socketserver.StreamRequestHandler):

    def handle(self):
        head = read_head(self.rfile)
        if head is None:
            return
        start, headers = parse_head(head)
        method, target, _ = start.split(" ", 2)
        url = urlsplit(target)
        if url.hostname is None:
            self.wfile.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
            return

        path = (url.path or "/") + (f"?{url.query}" if url.query else "")
        up = socket.create_connection((url.hostname, url.port or 80),
                                      timeout=30)
        out = [f"{method} {path} HTTP/1.1".encode("latin-1")]
        for k, v in headers:
            if k.lower() == "proxy-connection":
                continue
            out.append(f"{k}: {v}".encode("latin-1"))
        up.sendall(b"\r\n".join(out) + b"\r\n\r\n")

        length = header(headers, "content-length")
        if length:
            up.sendall(self.rfile.read(int(length)))

        self.relay(up, method, path)
        up.close()

    def relay(self, up, method, path):
        upf = up.makefile("rb")
        head = read_head(upf)
        if head is None:
            return
        start, headers = parse_head(head)
        self.wfile.write(head)
        self.wfile.flush()

        ctype = (header(headers, "content-type") or "").lower()
        print(f"--- {method} {path} -> {start}", file=sys.stderr)
        if not ctype.startswith("text/event-stream"):
            self.pump(up)
            return

        buf = b""
        seq = 0
        last = time.monotonic()
        while True:
            chunk = up.recv(4096)
            if not chunk:
                break
            self.wfile.write(chunk)
            self.wfile.flush()
            buf += chunk
            while True:
                block, rest = sseframe.split_block(buf)
                if block is None:
                    break
                buf = rest
                fields, comments = sseframe.parse_block(block)
                now = time.monotonic()
                if fields:
                    seq += 1
                    print(f"  #{seq:<4} +{now - last:7.3f}s  "
                          f"{sseframe.data_of(fields)!r}",
                          file=sys.stderr)
                    last = now
                else:
                    for c in comments:
                        print(f"  :     +{now - last:7.3f}s  "
                              f"keep-alive {c!r}", file=sys.stderr)

    def pump(self, up):
        while True:
            chunk = up.recv(16384)
            if not chunk:
                return
            self.wfile.write(chunk)
            self.wfile.flush()


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8080)
    args = ap.parse_args()
    with Server((args.host, args.port), Handler) as srv:
        print(f"listening on {args.host}:{args.port}", file=sys.stderr)
        srv.serve_forever()


if __name__ == "__main__":
    main()
