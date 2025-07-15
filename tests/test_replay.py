import urllib.request

from sseint import session
from sseint.decoders.sse import SSEDecoder
from sseint.replay import ReplayServer, gaps, write_stream


class FakeFile:
    def __init__(self):
        self.data = b""

    def write(self, b):
        self.data += b

    def flush(self):
        pass


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.slept = []

    def __call__(self):
        return self.now

    def sleep(self, s):
        self.slept.append(round(s, 4))
        self.now += s


def recorded(raw: bytes, times):
    d = SSEDecoder()
    frames = d.feed(raw) + d.close()
    for f, t in zip(frames, times):
        f.t = t
    return frames


def test_gaps_are_differences_not_absolute_times():
    frames = recorded(b"data: a\n\ndata: b\n\ndata: c\n\n",
                      [0.0, 1.0, 1.25])
    assert [round(g, 4) for _, g in gaps(frames)] == [0.0, 1.0, 0.25]


def test_speed_divides_the_gaps():
    frames = recorded(b"data: a\n\ndata: b\n\n", [0.0, 2.0])
    assert [round(g, 4) for _, g in gaps(frames, speed=4)] == [0.0, 0.5]


def test_pacing_does_not_accumulate_drift():
    frames = recorded(b"data: a\n\ndata: b\n\ndata: c\n\n",
                      [0.0, 1.0, 2.0])
    clock = FakeClock()
    out = FakeFile()

    def slow_write(b):
        clock.now += 0.4          # pretend the write took 400ms
        out.data += b

    fh = FakeFile()
    fh.write = slow_write
    write_stream(frames, fh, sleep=clock.sleep, clock=clock)
    # Without pacing against a single start time the third frame would
    # land at 2.8s; the sleeps have to shrink instead.
    assert clock.now <= 2.45


def test_serves_a_recorded_exchange(tmp_path):
    path = tmp_path / "s.jsonl"
    from sseint.tap import Exchange
    e = Exchange(n=1, host="h", method="GET", path="/s",
                 status="HTTP/1.1 200 OK",
                 headers=[("content-type", "text/event-stream")],
                 decoder="sse")
    w = session.SessionWriter(path)
    w.exchange(e)
    for f in recorded(b"data: a\n\ndata: [DONE]\n\n", [0.0, 0.0]):
        e.frames.append(f)
        w.frame(e, f)
    w.end(e)
    w.close()

    _, exchanges = session.read(path)
    with ReplayServer(exchanges[0], speed=1000.0) as srv:
        url = f"http://127.0.0.1:{srv.port}/s"
        body = urllib.request.urlopen(url, timeout=5).read()
    assert b"data: a" in body
    assert b"[DONE]" in body
