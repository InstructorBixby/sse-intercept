from sseint import session
from sseint.decoders.sse import SSEDecoder
from sseint.tap import Exchange


def exchange(n=1):
    return Exchange(n=n, host="h", method="GET", path="/s",
                    status="HTTP/1.1 200 OK",
                    headers=[("content-type", "text/event-stream")],
                    decoder="sse")


def frames(count):
    raw = b"".join(f"data: frame-{i}\n\n".encode()
                   for i in range(count))
    d = SSEDecoder()
    return d.feed(raw) + d.close()


def write(path, count, max_bytes):
    w = session.SessionWriter(path, max_bytes=max_bytes)
    ex = exchange()
    w.exchange(ex)
    for f in frames(count):
        ex.frames.append(f)
        w.frame(ex, f)
    w.end(ex)
    w.close()


def test_rotation_happens(tmp_path):
    path = tmp_path / "s.jsonl"
    write(path, 60, max_bytes=800)
    assert (tmp_path / "s.jsonl.1").exists()


def test_a_rotated_session_reads_as_one_session(tmp_path):
    path = tmp_path / "s.jsonl"
    write(path, 60, max_bytes=800)
    _, exchanges = session.read(path)
    assert len(exchanges) == 1
    assert [f.data for f in exchanges[0].frames][:2] == \
        ["frame-0", "frame-1"]
    assert len(exchanges[0].frames) == 60


def test_follow_can_be_turned_off(tmp_path):
    path = tmp_path / "s.jsonl"
    write(path, 60, max_bytes=800)
    _, whole = session.read(path)
    _, first = session.read(path, follow=False)
    assert len(first[0].frames) < len(whole[0].frames)


def test_no_rotation_without_a_limit(tmp_path):
    path = tmp_path / "s.jsonl"
    write(path, 60, max_bytes=None)
    assert not (tmp_path / "s.jsonl.1").exists()


def test_a_missing_continuation_is_not_fatal(tmp_path):
    path = tmp_path / "s.jsonl"
    write(path, 60, max_bytes=800)
    (tmp_path / "s.jsonl.1").unlink()
    _, exchanges = session.read(path)
    assert exchanges and exchanges[0].frames
