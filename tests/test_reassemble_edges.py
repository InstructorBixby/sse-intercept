from sseint.decoders.sse import SSEDecoder
from sseint.reassemble import describe, reassemble


def frames(raw: bytes):
    d = SSEDecoder()
    return d.feed(raw) + d.close()


def test_keepalive_only_stream():
    d = describe(frames(b": ping\n\n: ping\n\n"))
    assert d["frames"] == 0
    assert d["keepalives"] == 2
    assert d["keepalive_only"] is True
    assert d["first_frame_s"] is None
    assert d["max_gap_s"] is None


def test_empty_stream():
    d = describe([])
    assert d["frames"] == 0
    assert d["keepalive_only"] is False


def test_reassembling_a_keepalive_only_stream_is_empty_not_an_error():
    assert reassemble(frames(b": ping\n\n")) == ""
