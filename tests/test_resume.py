from sseint.decoders.sse import SSEDecoder
from sseint.resume import analyse, last_id
from sseint.session import Exchange


def exchange(n, raw: bytes, request_headers=()):
    ex = Exchange({"ex": n, "host": "h", "method": "GET",
                   "path": "/stream", "status": "HTTP/1.1 200 OK",
                   "decoder": "sse",
                   "request_headers": [list(h) for h in request_headers]})
    d = SSEDecoder()
    ex.frames = d.feed(raw) + d.close()
    return ex


FIRST = b"id: 1\ndata: Hel\n\nid: 2\ndata: lo\n\n"


def test_last_id():
    assert last_id(exchange(1, FIRST).frames) == "2"


def test_no_header_means_no_resume():
    second = exchange(2, b"id: 1\ndata: Hel\n\n")
    r = analyse([exchange(1, FIRST), second])[0]
    assert r.last_id_sent is None
    assert "without Last-Event-ID" in r.verdict()
    assert r.overlap == 3


def test_correct_resume():
    second = exchange(2, b"id: 3\ndata: there\n\n",
                      [("last-event-id", "2")])
    r = analyse([exchange(1, FIRST), second])[0]
    assert r.resumed
    assert r.verdict() == "resumed correctly"


def test_server_ignores_the_header():
    second = exchange(2, b"id: 1\ndata: Hello\n\n",
                      [("last-event-id", "2")])
    r = analyse([exchange(1, FIRST), second])[0]
    assert not r.resumed
    assert "restarted anyway" in r.verdict()


def test_wrong_id_is_called_out():
    second = exchange(2, b"id: 3\ndata: x\n\n",
                      [("Last-Event-ID", "9")])
    r = analyse([exchange(1, FIRST), second])[0]
    assert "but the last id it received" in r.verdict()


def test_a_different_path_is_not_a_reconnect():
    second = exchange(2, b"data: x\n\n")
    second.path = "/other"
    assert analyse([exchange(1, FIRST), second]) == []
