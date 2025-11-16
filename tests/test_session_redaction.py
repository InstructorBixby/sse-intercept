from sseint import session
from sseint.tap import Exchange


def ex():
    return Exchange(n=1, host="h", method="POST", path="/s",
                    status="HTTP/1.1 200 OK",
                    headers=[("set-cookie", "s=deadbeef"),
                             ("content-type", "text/event-stream")],
                    decoder="sse")


def test_redacted_by_default(tmp_path):
    path = tmp_path / "s.jsonl"
    w = session.SessionWriter(path)
    w.exchange(ex(), request_headers=[("authorization", "Bearer xyz123")])
    w.close()
    text = path.read_text()
    assert "xyz123" not in text
    assert "deadbeef" not in text
    assert "text/event-stream" in text


def test_opting_out_is_recorded_in_the_file(tmp_path):
    path = tmp_path / "s.jsonl"
    w = session.SessionWriter(path, redact_headers=False)
    w.exchange(ex(), request_headers=[("authorization", "Bearer xyz123")])
    w.close()
    meta, _ = session.read(path)
    assert meta["redacted"] is False
    assert "credentials" in meta["warning"]
    assert "xyz123" in path.read_text()
