"""Proxy core: CONNECT, TLS interception, and an unbuffered relay.

The relay is the part that matters. Bytes go out to the client the
moment they arrive, and a copy goes to the decoder. Anything that
reverses that order -- decode, then forward -- turns the tool into the
thing it was written to replace.
"""
from __future__ import annotations

import socket
import socketserver
import ssl
import threading
from urllib.parse import urlsplit

from sseint import tls
from sseint.decoders import by_name, for_content_type
from sseint.encoding import Inflater
from sseint.scope import Scope

HOP_BY_HOP = {
    "proxy-connection", "keep-alive", "proxy-authenticate",
    "proxy-authorization", "te", "trailers", "upgrade",
}


def read_head(rfile) -> bytes | None:
    buf = b""
    while b"\r\n\r\n" not in buf:
        b = rfile.read(1)
        if not b:
            return None
        buf += b
        if len(buf) > 65536:
            raise ValueError("message head too large")
    return buf


def parse_head(head: bytes):
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

    timeout = 300

    @property
    def tap(self):
        return self.server.tap

    def handle(self):
        head = read_head(self.rfile)
        if head is None:
            return
        start, headers = parse_head(head)
        try:
            method, target, _ = start.split(" ", 2)
        except ValueError:
            self.deny(400, "bad request line")
            return
        if method == "CONNECT":
            self.do_connect(target)
        else:
            self.do_plain(method, target, headers)

    def deny(self, code: int, why: str):
        body = f"sse-intercept: {why}\n".encode()
        self.wfile.write(
            f"HTTP/1.1 {code} Forbidden\r\n"
            f"content-type: text/plain\r\n"
            f"content-length: {len(body)}\r\n"
            f"connection: close\r\n\r\n".encode("latin-1"))
        self.wfile.write(body)
        self.wfile.flush()

    def do_connect(self, authority: str):
        host, _, port = authority.rpartition(":")
        port = int(port or 443)
        if not self.server.scope.allows(host):
            self.tap.refused(host)
            self.deny(403, f"{host} is not in --allow-host")
            return
        self.wfile.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        self.wfile.flush()

        ctx = self.server.certs.context_for(host)
        try:
            tls_sock = ctx.wrap_socket(self.connection, server_side=True)
        except ssl.SSLError as exc:
            self.tap.handshake_failed(host, str(exc))
            return

        up = socket.create_connection((host, port), timeout=30)
        up = tls.client_context().wrap_socket(up, server_hostname=host)

        rfile = tls_sock.makefile("rb")
        wfile = tls_sock.makefile("wb")
        try:
            head = read_head(rfile)
            if head is None:
                return
            start, headers = parse_head(head)
            method, target, _ = start.split(" ", 2)
            self.forward(up, method, target, headers, rfile)
            self.relay(up, wfile, host, method, target)
        finally:
            up.close()

    def do_plain(self, method, target, headers):
        url = urlsplit(target)
        if url.hostname is None:
            self.deny(400, "absolute-form URI required")
            return
        if not self.server.scope.allows(url.hostname):
            self.tap.refused(url.hostname)
            self.deny(403, f"{url.hostname} is not in --allow-host")
            return
        up = socket.create_connection((url.hostname, url.port or 80),
                                      timeout=30)
        path = (url.path or "/") + (f"?{url.query}" if url.query else "")
        self.forward(up, method, path, headers, self.rfile)
        self.relay(up, self.wfile, url.hostname, method, path)
        up.close()

    def forward(self, up, method, path, headers, rfile):
        if path.startswith("http"):
            u = urlsplit(path)
            path = (u.path or "/") + (f"?{u.query}" if u.query else "")
        out = [f"{method} {path} HTTP/1.1".encode("latin-1")]
        for k, v in headers:
            if k.lower() in HOP_BY_HOP:
                continue
            out.append(f"{k}: {v}".encode("latin-1"))
        up.sendall(b"\r\n".join(out) + b"\r\n\r\n")
        length = header(headers, "content-length")
        if length:
            up.sendall(rfile.read(int(length)))

    def relay(self, up, wfile, host, method, path):
        upf = up.makefile("rb")
        head = read_head(upf)
        if head is None:
            return
        start, headers = parse_head(head)
        wfile.write(head)
        wfile.flush()

        ctype = header(headers, "content-type")
        decoder = (by_name(self.server.force_decoder)
                   if self.server.force_decoder
                   else for_content_type(ctype))
        inflater = Inflater(header(headers, "content-encoding"))
        ex = self.tap.exchange(host=host, method=method, path=path,
                               status=start, headers=headers,
                               decoder=decoder.name if decoder else None)
        reported = False
        try:
            while True:
                chunk = up.recv(16384)
                if not chunk:
                    break
                wfile.write(chunk)
                wfile.flush()
                if decoder is None:
                    continue
                body = inflater.feed(chunk)
                if not reported and inflater.mismatch:
                    self.tap.note(ex, inflater.mismatch)
                    reported = True
                for frame in decoder.feed(body):
                    self.tap.frame(ex, frame)
            if decoder is not None:
                tail = inflater.close()
                if tail:
                    for frame in decoder.feed(tail):
                        self.tap.frame(ex, frame)
                for frame in decoder.close():
                    self.tap.frame(ex, frame)
        finally:
            self.tap.end(ex)


class Server(socketserver.ThreadingTCPServer):

    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, addr, scope: Scope, certs, tap,
                 force_decoder: str | None = None):
        self.scope = scope
        self.certs = certs
        self.tap = tap
        self.force_decoder = force_decoder
        self.lock = threading.Lock()
        super().__init__(addr, Handler)
