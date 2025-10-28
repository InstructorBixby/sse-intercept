import json

from sseint import session
from sseint.cli import main
from sseint.decoders.sse import SSEDecoder
from sseint.tap import Exchange


def write_session(path):
    w = session.SessionWriter(path)
    ex = Exchange(n=1, host="api.example.test", method="POST",
                  path="/v1/stream", status="HTTP/1.1 200 OK",
                  headers=[("content-type", "text/event-stream")],
                  decoder="sse")
    w.exchange(ex)
    d = SSEDecoder()
    for f in d.feed(b"data: Hel\n\ndata: lo\n\n") + d.close():
        ex.frames.append(f)
        w.frame(ex, f)
    w.end(ex)
    w.close()


def test_export_to_a_file(tmp_path):
    s = tmp_path / "s.jsonl"
    out = tmp_path / "out.har"
    write_session(s)
    assert main(["export", str(s), "--out", str(out)]) == 0
    doc = json.loads(out.read_text())
    assert doc["log"]["entries"][0]["response"]["content"]["text"] == \
        "Hello"


def test_export_to_stdout(tmp_path, capsys):
    s = tmp_path / "s.jsonl"
    write_session(s)
    assert main(["export", str(s)]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["log"]["version"] == "1.2"


def test_unknown_exchange_is_an_error(tmp_path):
    s = tmp_path / "s.jsonl"
    write_session(s)
    assert main(["export", str(s), "--exchange", "9"]) == 2
