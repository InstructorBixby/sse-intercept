from sseint.decoders.sse import SSEDecoder, is_done, retry_of


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def decode(chunks, clock=None):
    d = SSEDecoder(clock=clock)
    out = []
    for c in chunks:
        out += d.feed(c)
    out += d.close()
    return out


def test_lf_and_crlf_in_one_stream():
    out = decode([b"data: a\r\n\r\ndata: b\n\n"])
    assert [f.data for f in out] == ["a", "b"]


def test_separator_split_across_reads():
    out = decode([b"data: a\r\n\r", b"\ndata: b\n\n"])
    assert [f.data for f in out] == ["a", "b"]


def test_missing_trailing_blank_line_still_yields_a_frame():
    out = decode([b"data: a\n\ndata: last"])
    assert [f.data for f in out] == ["a", "last"]
    assert out[-1].note == "eof"


def test_comment_frames_are_kind_comment():
    out = decode([b": ping\n\n"])
    assert out[0].kind == "comment"
    assert out[0].comments == [" ping"]


def test_relative_timing():
    clock = Clock()
    d = SSEDecoder(clock=clock)
    d.feed(b"data: a\n\n")
    clock.now = 1.5
    frames = d.feed(b"data: b\n\n")
    assert frames[0].t == 1.5


def test_retry_and_done():
    out = decode([b"retry: 2500\n\ndata: [DONE]\n\n"])
    assert retry_of(out[0]) == 2500
    assert is_done(out[1])


def test_waiting_on_boundary_is_distinguishable_from_a_stall():
    d = SSEDecoder()
    d.feed(b"data: a\r\n\r")
    assert d.waiting_on_boundary
    d.feed(b"\n")
    assert not d.waiting_on_boundary
