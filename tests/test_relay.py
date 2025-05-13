from sseint.decoders.sse import SSEDecoder
from sseint.encoding import Inflater
from sseint.rules import Context, Cut, Delay, Drop, Engine, Match, Rule


class FakeFile:
    def __init__(self):
        self.data = b""

    def write(self, b):
        self.data += b

    def flush(self):
        pass


class FakeTap:
    paused = False

    def __init__(self):
        self.frames = []
        self.notes = []

    def frame(self, ex, frame, **kw):
        self.frames.append((frame, kw))

    def note(self, ex, text):
        self.notes.append(text)


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.slept = []

    def __call__(self):
        return self.now

    def sleep(self, s):
        self.slept.append(s)
        self.now += s


def build(engine=None, tap=None, clock=None):
    from sseint.relay import Relay
    clock = clock or FakeClock()
    return Relay(SSEDecoder(clock=clock), Inflater(None),
                 tap or FakeTap(), object(), engine,
                 Context(host="h", path="/p"),
                 sleep=clock.sleep, clock=clock), clock


def test_passthrough_without_an_engine():
    relay, _ = build()
    out = FakeFile()
    relay.chunk(b"data: a\n\n", out)
    assert out.data == b"data: a\n\n"


def test_drop_removes_the_frame_from_the_wire():
    relay, _ = build(Engine([Rule("r", Match(seq=1), [Drop()])]))
    out = FakeFile()
    relay.chunk(b"data: a\n\ndata: b\n\n", out)
    assert out.data == b"data: b\r\n\r\n"


def test_delay_sleeps_and_is_reported_as_added_latency():
    relay, clock = build(Engine([Rule("r", Match(seq=1), [Delay(750)])]))
    tap = relay.tap
    relay.chunk(b"data: a\n\n", FakeFile())
    assert clock.slept == [0.75]
    assert tap.frames[0][1]["added_ms"] == 750


def test_cut_stops_the_stream():
    relay, _ = build(Engine([Rule("r", Match(seq=2), [Cut()])]))
    out = FakeFile()
    assert relay.chunk(b"data: a\n\ndata: b\n\ndata: c\n\n",
                       out) is False
    assert out.data == b"data: a\r\n\r\n"
    assert relay.chunk(b"data: d\n\n", out) is False


def test_pause_releases_when_the_budget_expires():
    tap = FakeTap()
    tap.paused = True
    from sseint.rules import Pause
    relay, clock = build(Engine([Rule("r", Match(seq=1), [Pause()])]),
                         tap=tap)
    relay.pause_budget_s = 1.0
    relay.chunk(b"data: a\n\n", FakeFile())
    assert any("budget" in n for n in tap.notes)
    assert tap.paused is False
