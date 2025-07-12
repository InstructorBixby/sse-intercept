from sseint import session
from sseint.decoders.sse import SSEDecoder
from sseint.tap import Exchange


def frames(raw: bytes):
    d = SSEDecoder()
    return d.feed(raw) + d.close()


def ex():
    return Exchange(n=1, host="api.example.test", method="POST",
                    path="/v1/stream", status="HTTP/1.1 200 OK",
                    headers=[("content-type", "text/event-stream")],
                    decoder="sse")


def test_roundtrip(tmp_path):
    path = tmp_path / "s.jsonl"
    w = session.SessionWriter(path)
    e = ex()
    w.exchange(e, request_headers=[("accept", "text/event-stream")])
    for f in frames(b"data: Hel\n\ndata: lo\n\n"):
        e.frames.append(f)
        w.frame(e, f)
    w.note(e, "something worth saying")
    w.end(e)
    w.close()

    meta, exchanges = session.read(path)
    assert meta["format"] == session.FORMAT
    assert len(exchanges) == 1
    got = exchanges[0]
    assert got.host == "api.example.test"
    assert [f.data for f in got.frames] == ["Hel", "lo"]
    assert got.notes == ["something worth saying"]
    assert got.request_headers == [("accept", "text/event-stream")]


def test_truncated_last_line_is_ignored(tmp_path):
    path = tmp_path / "s.jsonl"
    w = session.SessionWriter(path)
    e = ex()
    w.exchange(e)
    for f in frames(b"data: a\n\n"):
        e.frames.append(f)
        w.frame(e, f)
    w.close()
    with path.open("a") as fh:
        fh.write('{"t":"frame","ex":1,"seq":2,"fi')

    _, exchanges = session.read(path)
    assert [f.data for f in exchanges[0].frames] == ["a"]


def test_non_utf8_frame_keeps_its_bytes(tmp_path):
    from sseint.frame import Frame
    path = tmp_path / "s.jsonl"
    w = session.SessionWriter(path)
    e = ex()
    w.exchange(e)
    f = Frame(seq=1, t=0.0, kind="chunk", raw=b"\xff\xfe",
              fields=[("data", "??")])
    e.frames.append(f)
    w.frame(e, f)
    w.end(e)
    w.close()
    _, exchanges = session.read(path)
    assert exchanges[0].frames[0].raw == b"\xff\xfe"
