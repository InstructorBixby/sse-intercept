from sseint import csvout
from sseint.decoders.sse import SSEDecoder
from sseint.session import Exchange


def exchange(raw: bytes, times=None):
    ex = Exchange({"ex": 1, "host": "api.example.test",
                   "method": "GET", "path": "/v1/stream",
                   "status": "200 OK", "decoder": "sse"})
    d = SSEDecoder()
    ex.frames = d.feed(raw) + d.close()
    for f, t in zip(ex.frames, times or []):
        f.t = t
    return ex


def test_header_and_one_row_per_frame():
    text = csvout.write([exchange(b"data: a\n\ndata: b\n\n",
                                  [0.0, 0.5])])
    lines = text.strip().split("\n")
    assert lines[0].startswith("exchange,host,path,seq")
    assert len(lines) == 3


def test_the_gap_is_computed_not_left_to_the_spreadsheet():
    text = csvout.write([exchange(b"data: a\n\ndata: b\n\n",
                                  [0.0, 0.5])])
    second = text.strip().split("\n")[2].split(",")
    assert second[6] == "0.5"


def test_the_first_frame_has_no_gap():
    text = csvout.write([exchange(b"data: a\n\n", [0.25])])
    first = text.strip().split("\n")[1].split(",")
    assert first[5] == "0.25"
    assert first[6] == ""


def test_keepalives_get_rows_too():
    text = csvout.write([exchange(b": ping\n\ndata: a\n\n",
                                  [0.0, 1.0])])
    assert "comment" in text
