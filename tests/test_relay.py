from sseint.decoders.sse import SSEDecoder
from sseint.encoding import Inflater
from sseint.relay import Relay
from sseint.rules import (Context, Cut, Delay, Drop, Engine, Match,
                          Pause, Rewrite, Rule)


class FakeTap:
    paused = False

    def __init__(self):
        self.frames = []
        self.notes = []
        self.ended = False

    def frame(self, ex, frame, **kw):
        self.frames.append((frame, kw))

    def note(self, ex, text):
        self.notes.append(text)

    def end(self, ex):
        self.ended = True


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.slept = []

    def __call__(self):
        return self.now

    def sleep(self, s):
        self.slept.append(round(s, 4))
        self.now += s


def build(engine=None, tap=None):
    clock = FakeClock()
    tap = tap or FakeTap()
    relay = Relay(SSEDecoder(clock=clock), Inflater(None), tap,
                  object(), engine, Context(host="h", path="/p"),
                  sleep=clock.sleep, clock=clock)
    return relay, tap, clock


def test_observation_returns_the_bytes_unchanged():
    relay, tap, _ = build()
    assert relay.feed(b"data: a\n\n") == b"data: a\n\n"
    assert len(tap.frames) == 1


def test_drop_removes_the_frame_from_the_wire():
    relay, _, _ = build(Engine([Rule("r", Match(seq=1), [Drop()])]))
    assert relay.feed(b"data: a\n\ndata: b\n\n") == \
        b"data: b\r\n\r\n"


def test_rewrite_reencodes_only_the_matching_frame():
    eng = Engine([Rule("r", Match(data_contains="a"),
                       [Rewrite("a", "z")])])
    relay, _, _ = build(eng)
    out = relay.feed(b"data: a\n\ndata: b\n\n")
    assert out == b"data: z\r\n\r\ndata: b\r\n\r\n"


def test_delay_is_reported_as_added_latency():
    relay, tap, clock = build(
        Engine([Rule("r", Match(seq=1), [Delay(750)])]))
    relay.feed(b"data: a\n\n")
    assert clock.slept == [0.75]
    assert tap.frames[0][1]["added_ms"] == 750


def test_cut_stops_the_stream():
    relay, _, _ = build(Engine([Rule("r", Match(seq=2), [Cut()])]))
    assert relay.feed(b"data: a\n\ndata: b\n\ndata: c\n\n") == \
        b"data: a\r\n\r\n"
    assert relay.feed(b"data: d\n\n") == b""
    assert relay.finish() == b""


def test_finish_flushes_a_stream_with_no_trailing_blank_line():
    relay, tap, _ = build()
    relay.feed(b"data: a\n\ndata: last")
    relay.finish()
    assert [f.data for f, _ in tap.frames] == ["a", "last"]


def test_pause_releases_when_the_budget_expires():
    tap = FakeTap()
    tap.paused = True
    relay, _, _ = build(Engine([Rule("r", Match(seq=1), [Pause()])]),
                        tap=tap)
    relay.pause_budget_s = 1.0
    relay.feed(b"data: a\n\n")
    assert any("budget" in n for n in tap.notes)
    assert tap.paused is False
