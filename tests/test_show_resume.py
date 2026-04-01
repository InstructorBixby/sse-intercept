from sseint.decoders.sse import SSEDecoder
from sseint.session import Exchange
from sseint.show import render


def exchange(n, raw: bytes, request_headers=()):
    ex = Exchange({"ex": n, "host": "h", "method": "GET",
                   "path": "/stream", "status": "HTTP/1.1 200 OK",
                   "decoder": "sse",
                   "request_headers": [list(h) for h in request_headers]})
    d = SSEDecoder()
    ex.frames = d.feed(raw) + d.close()
    return ex


META = {"format": 2, "tool_version": "1.1.0", "redacted": True}


def test_resume_section():
    out = render(META, [
        exchange(1, b"id: 1\ndata: Hel\n\n"),
        exchange(2, b"id: 1\ndata: Hel\n\nid: 2\ndata: lo\n\n"),
    ], resume=True)
    assert "reconnects:" in out
    assert "without Last-Event-ID" in out


def test_no_reconnects_says_so():
    out = render(META, [exchange(1, b"data: a\n\n")], resume=True)
    assert "no reconnects" in out


def test_header_line_reports_redaction():
    assert "redacted=True" in render(META, [], resume=True)
