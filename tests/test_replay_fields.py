import urllib.request

from sseint.decoders.sse import SSEDecoder
from sseint.replay import ReplayServer
from sseint.session import Exchange


def exchange(raw: bytes):
    ex = Exchange({"ex": 1, "host": "h", "method": "GET",
                   "path": "/s", "status": "200 OK", "decoder": "sse",
                   "response_headers": [
                       ["content-type", "text/event-stream"],
                       ["content-length", "99"],
                       ["content-encoding", "gzip"]]})
    d = SSEDecoder()
    ex.frames = d.feed(raw) + d.close()
    for f in ex.frames:
        f.t = 0.0
    return ex


RAW = (b"retry: 2500\n\n"
       b"id: 41\nevent: token\ndata: Hel\n\n"
       b"id: 42\nevent: token\ndata: lo\n\n"
       b"data: [DONE]\n\n")


def fetch():
    with ReplayServer(exchange(RAW), speed=1e9) as srv:
        url = f"http://127.0.0.1:{srv.port}/s"
        resp = urllib.request.urlopen(url, timeout=5)
        return resp.read(), resp.headers


def test_ids_and_retry_survive_a_replay():
    body, _ = fetch()
    assert b"retry: 2500" in body
    assert b"id: 41" in body
    assert b"id: 42" in body
    assert b"event: token" in body


def test_framing_headers_are_not_replayed():
    _, headers = fetch()
    assert headers.get("content-encoding") is None
    assert headers.get("content-type") == "text/event-stream"
