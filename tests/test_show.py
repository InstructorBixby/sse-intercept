from sseint.decoders.sse import SSEDecoder
from sseint.session import Exchange
from sseint.show import render


def exchange(raw: bytes, times=None):
    ex = Exchange({"ex": 1, "host": "api.example.test",
                   "method": "POST", "path": "/v1/stream",
                   "status": "HTTP/1.1 200 OK", "decoder": "sse"})
    d = SSEDecoder()
    ex.frames = d.feed(raw) + d.close()
    for f, t in zip(ex.frames, times or []):
        f.t = t
    return ex


META = {"format": 1, "tool_version": "0.5.0"}


def test_frame_listing():
    out = render(META, [exchange(b"data: a\n\ndata: b\n\n")])
    assert "#1" in out and "#2" in out
    assert "/v1/stream" in out


def test_timing_mode_replaces_the_listing():
    out = render(META, [exchange(b"data: a\n\ndata: b\n\n",
                                 [0.0, 2.0])], timing=True)
    assert "gap p50" in out
    assert "#2" not in out


def test_reassemble_mode():
    out = render(META, [exchange(b"data: Hel\n\ndata: lo\n\n")],
                 reassemble_mode="data")
    assert "Hello" in out


def test_only_filters_by_exchange():
    a = exchange(b"data: a\n\n")
    b = exchange(b"data: b\n\n")
    b.n = 2
    out = render(META, [a, b], only=2)
    assert "[2]" in out and "[1]" not in out


def test_stall_shows_up_in_timing():
    out = render(META, [exchange(b"data: a\n\ndata: b\n\n",
                                 [0.0, 9.0])], timing=True)
    assert "stall" in out
