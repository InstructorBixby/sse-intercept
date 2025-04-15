from sseint.decoders.sse import SSEDecoder
from sseint.reassemble import describe, reassemble


def frames(raw: bytes):
    d = SSEDecoder()
    return d.feed(raw) + d.close()


def test_data_concatenation():
    f = frames(b"data: Hel\n\ndata: lo\n\ndata: [DONE]\n\n")
    assert reassemble(f) == "Hello"


def test_keepalives_are_not_content():
    f = frames(b": ping\n\ndata: a\n\n")
    assert reassemble(f) == "a"


def test_lines_mode():
    f = frames(b"data: one\n\ndata: two\n\n")
    assert reassemble(f, "lines") == "one\ntwo"


def test_json_path_mode():
    raw = (b'data: {"choices":[{"delta":{"content":"Hel"}}]}\n\n'
           b'data: {"choices":[{"delta":{"content":"lo"}}]}\n\n'
           b'data: [DONE]\n\n')
    got = reassemble(frames(raw), "json:choices.0.delta.content")
    assert got == "Hello"


def test_json_path_tolerates_a_frame_without_the_path():
    raw = (b'data: {"choices":[{"delta":{"role":"assistant"}}]}\n\n'
           b'data: {"choices":[{"delta":{"content":"hi"}}]}\n\n')
    got = reassemble(frames(raw), "json:choices.0.delta.content")
    assert got == "hi"


def test_describe():
    d = describe(frames(b": ping\n\ndata: a\n\ndata: [DONE]\n\n"))
    assert d["frames"] == 2
    assert d["keepalives"] == 1
    assert d["done_sentinel"] is True
    assert d["truncated"] is False


def test_describe_flags_a_truncated_stream():
    d = describe(frames(b"data: a\n\ndata: cut off"))
    assert d["truncated"] is True
    assert d["done_sentinel"] is False
