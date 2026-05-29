from sseint.decoders.sse import SSEDecoder
from sseint.session import Exchange
from sseint.show import render

META = {"format": 2, "tool_version": "1.2.0", "redacted": True}


def exchange(raw: bytes):
    ex = Exchange({"ex": 1, "host": "h", "method": "GET",
                   "path": "/s", "status": "HTTP/1.1 200 OK",
                   "decoder": "sse"})
    d = SSEDecoder()
    ex.frames = d.feed(raw) + d.close()
    return ex


HIDDEN = "data: hel\u200blo\n\n".encode()


def test_flagged_even_without_the_flag():
    out = render(META, [exchange(HIDDEN)])
    assert "invisible or formatting codepoints in frame(s) 1" in out


def test_visible_renders_the_marker():
    out = render(META, [exchange(HIDDEN)], show_invisible=True)
    assert "<ZWSP>" in out


def test_clean_stream_says_nothing():
    out = render(META, [exchange(b"data: hello\n\n")])
    assert "invisible" not in out


def test_visible_applies_to_the_reassembled_message_too():
    out = render(META, [exchange(HIDDEN)], reassemble_mode="data",
                 show_invisible=True)
    assert "hel<ZWSP>lo" in out
