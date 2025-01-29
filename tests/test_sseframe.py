import sseframe


def feed(chunks):
    """Run chunks through the splitter the way the proxy does."""
    buf = b""
    out = []
    for chunk in chunks:
        buf += chunk
        while True:
            block, rest = sseframe.split_block(buf)
            if block is None:
                break
            buf = rest
            out.append(sseframe.parse_block(block))
    return out, buf


def test_lf_separator():
    out, rest = feed([b"data: a\n\ndata: b\n\n"])
    assert [sseframe.data_of(f) for f, _ in out] == ["a", "b"]
    assert rest == b""


def test_crlf_separator():
    out, _ = feed([b"data: a\r\n\r\n"])
    assert sseframe.data_of(out[0][0]) == "a"


def test_mixed_separators_in_one_stream():
    out, _ = feed([b"data: a\r\n\r\ndata: b\n\n"])
    assert [sseframe.data_of(f) for f, _ in out] == ["a", "b"]


def test_separator_split_across_reads():
    out, rest = feed([b"data: a\r\n\r", b"\ndata: b\r\n\r\n"])
    assert [sseframe.data_of(f) for f, _ in out] == ["a", "b"]
    assert rest == b""


def test_frame_split_across_reads():
    out, _ = feed([b"data: hel", b"lo world\n\n"])
    assert sseframe.data_of(out[0][0]) == "hello world"


def test_comment_is_not_a_frame():
    out, _ = feed([b": keep-alive\n\ndata: a\n\n"])
    assert out[0][0] == []
    assert out[0][1] == [" keep-alive"]
    assert sseframe.data_of(out[1][0]) == "a"


def test_multi_line_data_joins_with_newline():
    out, _ = feed([b"data: one\ndata: two\n\n"])
    assert sseframe.data_of(out[0][0]) == "one\ntwo"


def test_one_leading_space_is_stripped_and_only_one():
    out, _ = feed([b"data:  two spaces\n\n"])
    assert sseframe.data_of(out[0][0]) == " two spaces"


def test_field_with_no_colon():
    out, _ = feed([b"data\n\n"])
    assert out[0][0] == [("data", "")]
