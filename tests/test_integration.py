"""End to end against the sample server, no proxy involved.

These exercise the decoder and the encoding path against the framing
that real servers produce. The proxy is not in the loop on purpose:
mitmproxy has its own test suite and what breaks here is framing.
"""
from __future__ import annotations

import threading
import urllib.request

import pytest

from samples.stream_server import serve
from sseint.decoders.sse import SSEDecoder
from sseint.encoding import Inflater
from sseint.reassemble import describe, reassemble


def drain(quirk):
    srv = serve(port=0, quirk=quirk)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{srv.server_address[1]}/stream"
        resp = urllib.request.urlopen(url, timeout=30)
        inflater = Inflater(resp.headers.get("content-encoding"))
        decoder = SSEDecoder()
        frames = []
        while True:
            chunk = resp.read(1024)
            if not chunk:
                break
            frames += decoder.feed(inflater.feed(chunk))
        tail = inflater.close()
        if tail:
            frames += decoder.feed(tail)
        frames += decoder.close()
        return frames, inflater
    finally:
        srv.shutdown()
        srv.server_close()


@pytest.mark.parametrize("quirk", [
    "none", "crlf", "no-final-blank", "split-separator",
    "keepalive", "gzip", "gzip-unlabelled", "content-length",
])
def test_message_survives_every_quirk(quirk):
    frames, _ = drain(quirk)
    text = reassemble(frames, "json:choices.0.delta.content")
    assert text == "The quick brown fox jumps over the lazy dog."


def test_sentinel_is_seen_even_without_a_trailing_blank_line():
    frames, _ = drain("no-final-blank")
    assert describe(frames)["done_sentinel"] is True


def test_missing_sentinel_is_reported():
    frames, _ = drain("no-sentinel")
    assert describe(frames)["done_sentinel"] is False


def test_keepalives_are_counted_separately():
    frames, _ = drain("keepalive")
    assert describe(frames)["keepalives"] >= 3


def test_stripped_content_encoding_is_detected():
    _, inflater = drain("gzip-unlabelled")
    assert inflater.mismatch is not None


def test_huge_frame_arrives_whole():
    frames, _ = drain("huge-frame")
    assert any(len(f.data) >= 200_000 for f in frames)
