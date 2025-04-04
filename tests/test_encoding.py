import zlib

from sseint.encoding import Inflater, sniff


def gzip_stream(parts):
    """Compress each part with a sync flush, the way a server does."""
    co = zlib.compressobj(wbits=16 + zlib.MAX_WBITS)
    out = []
    for p in parts:
        out.append(co.compress(p) + co.flush(zlib.Z_SYNC_FLUSH))
    out.append(co.flush())
    return out


def test_identity_passes_through():
    inf = Inflater(None)
    assert inf.feed(b"data: a\n\n") == b"data: a\n\n"


def test_gzip_yields_frames_as_they_arrive():
    parts = gzip_stream([b"data: a\n\n", b"data: b\n\n"])
    inf = Inflater("gzip")
    got = b"".join(inf.feed(p) for p in parts) + inf.close()
    assert got == b"data: a\n\ndata: b\n\n"
    first = Inflater("gzip").feed(parts[0])
    assert b"data: a" in first


def test_stripped_header_is_detected_and_reported():
    parts = gzip_stream([b"data: a\n\n"])
    inf = Inflater(None)
    out = inf.feed(parts[0])
    assert b"data: a" in out
    assert inf.mismatch is not None
    assert "no Content-Encoding" in inf.mismatch


def test_sniff():
    assert sniff(b"\x1f\x8bxx") == "gzip"
    assert sniff(zlib.compress(b"hello")[:4]) == "deflate"
    assert sniff(b"data") is None
