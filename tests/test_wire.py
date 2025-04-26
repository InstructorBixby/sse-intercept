from sseint.decoders.sse import SSEDecoder
from sseint.wire import encode, encode_text


def roundtrip(raw: bytes) -> bytes:
    d = SSEDecoder()
    frames = d.feed(raw) + d.close()
    return b"".join(encode(f) for f in frames)


def test_simple_roundtrip():
    assert roundtrip(b"data: a\r\n\r\n") == b"data: a\r\n\r\n"


def test_multi_line_data_becomes_several_data_lines():
    out = roundtrip(b"data: one\ndata: two\n\n")
    assert out == b"data: one\r\ndata: two\r\n\r\n"


def test_fields_keep_wire_order():
    out = roundtrip(b"id: 3\nevent: token\ndata: x\n\n")
    assert out == b"id: 3\r\nevent: token\r\ndata: x\r\n\r\n"


def test_comment_frame_stays_a_comment():
    assert roundtrip(b": ping\n\n") == b": ping\r\n\r\n"


def test_roundtrip_is_reparseable():
    once = roundtrip(b"data: one\ndata: two\n\n")
    assert roundtrip(once) == once


def test_encode_text_adds_the_terminator():
    assert encode_text("data: hi") == b"data: hi\r\n\r\n"
    assert encode_text("data: hi\n") == b"data: hi\r\n\r\n"
