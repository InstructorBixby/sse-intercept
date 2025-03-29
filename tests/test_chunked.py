from sseint.decoders.chunked import ChunkedDecoder


def decode(chunks):
    d = ChunkedDecoder()
    out = []
    for c in chunks:
        out += d.feed(c)
    out += d.close()
    return out


def test_one_frame_per_chunk():
    out = decode([b"5\r\nhello\r\n5\r\nworld\r\n0\r\n\r\n"])
    assert [f.data for f in out[:2]] == ["hello", "world"]
    assert out[-1].note == "last-chunk"


def test_chunk_split_across_reads():
    out = decode([b"5\r\nhel", b"lo\r\n"])
    assert [f.data for f in out] == ["hello"]


def test_chunk_extension_is_ignored():
    out = decode([b"5;junk=1\r\nhello\r\n"])
    assert [f.data for f in out] == ["hello"]


def test_not_actually_chunked():
    out = decode([b"plain body\r\nmore\r\n"])
    assert out[0].note == "not-chunked"
