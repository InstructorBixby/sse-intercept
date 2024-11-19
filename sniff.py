"""Forward HTTP and print SSE frames as they arrive."""
import argparse
import socket
import socketserver
import sys
import time
from urllib.parse import urlsplit


def read_head(rfile):
    """Read up to and including the blank line that ends a message head."""
    buf = b""
    while b"\r\n\r\n" not in buf:
        b = rfile.read(1)
        if not b:
            return None
        buf += b
    return buf


def parse_head(head):
    lines = head.decode("latin-1").split("\r\n")
    start = lines[0]
    headers = []
    for line in lines[1:]:
        if not line:
            continue
        name, _, value = line.partition(":")
        headers.append((name.strip(), value.strip()))
    return start, headers


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
        host = url.hostname
        port = url.port or 80
        if host is None:
            self.wfile.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
            return

        path = url.path or "/"
        if url.query:
            path += "?" + url.query

        up = socket.create_connection((host, port), timeout=30)
        out = [f"{method} {path} HTTP/1.1".encode("latin-1")]
        for k, v in headers:
            if k.lower() in ("proxy-connection",):
                continue
            out.append(f"{k}: {v}".encode("latin-1"))
        up.sendall(b"\r\n".join(out) + b"\r\n\r\n")

        body_len = header(headers, "content-length")
        if body_len:
            up.sendall(self.rfile.read(int(body_len)))

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
        streaming = ctype.startswith("text/event-stream")
        print(f"--- {method} {path} -> {start}", file=sys.stderr)

        buf = b""
        t0 = time.monotonic()
        last = t0
        while True:
            chunk = up.recv(4096)
            if not chunk:
                break
            self.wfile.write(chunk)
            self.wfile.flush()
            if not streaming:
                continue
            buf += chunk
            while b"\n\n" in buf:
                block, buf = buf.split(b"\n\n", 1)
                now = time.monotonic()
                print(f"  +{now - last:7.3f}s  {block!r}",
                      file=sys.stderr)
                last = now


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
