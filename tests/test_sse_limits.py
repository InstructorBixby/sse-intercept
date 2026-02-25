from sseint.decoders.sse import SSEDecoder


def test_a_body_with_no_separator_is_surrendered_at_the_cap():
    d = SSEDecoder(max_frame_bytes=64)
    frames = d.feed(b"x" * 100)
    assert len(frames) == 1
    assert frames[0].note == "overlong"
    assert d.buffered == 0


def test_the_cap_does_not_fire_on_normal_framing():
    d = SSEDecoder(max_frame_bytes=64)
    frames = d.feed(b"data: short\n\n")
    assert [f.note for f in frames] == [None]


def test_a_legitimately_large_frame_still_arrives_whole():
    d = SSEDecoder()
    payload = "y" * 200_000
    frames = d.feed(f"data: {payload}\n\n".encode())
    assert frames[0].data == payload
    assert frames[0].note is None


def test_buffered_reports_what_is_held():
    d = SSEDecoder()
    d.feed(b"data: partial")
    assert d.buffered == len(b"data: partial")
