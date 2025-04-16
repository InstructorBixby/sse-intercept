from sseint.decoders.sse import SSEDecoder
from sseint.rules import (Context, Cut, Delay, Drop, Engine, Inject,
                          Match, Rewrite, Rule)


def frames(raw: bytes):
    d = SSEDecoder()
    return d.feed(raw) + d.close()


CTX = Context(host="api.example.test", path="/v1/stream")


def test_match_on_seq():
    eng = Engine([Rule("r", Match(seq=2), [Drop()])])
    got = [eng.decide(f, CTX)[0] for f in
           frames(b"data: a\n\ndata: b\n\ndata: c\n\n")]
    assert got == [[], [Drop()], []]


def test_match_on_data_contains():
    eng = Engine([Rule("r", Match(data_contains="secret"), [Drop()])])
    f = frames(b"data: a secret thing\n\n")[0]
    assert eng.decide(f, CTX)[0] == [Drop()]


def test_match_on_regex():
    eng = Engine([Rule("r", Match(data_matches=r"tok-\d+"), [Drop()])])
    assert eng.decide(frames(b"data: tok-41\n\n")[0], CTX)[0]
    assert not eng.decide(frames(b"data: tok-x\n\n")[0], CTX)[0]


def test_host_and_path_globs():
    eng = Engine([Rule("r", Match(host="*.example.test",
                                  path="/v1/*"), [Drop()])])
    assert eng.decide(frames(b"data: a\n\n")[0], CTX)[0]
    other = Context(host="api.other.test", path="/v1/stream")
    assert not eng.decide(frames(b"data: a\n\n")[0], other)[0]


def test_limit():
    eng = Engine([Rule("r", Match(kind="event"), [Drop()], limit=2)])
    got = [bool(eng.decide(f, CTX)[0]) for f in
           frames(b"data: a\n\ndata: b\n\ndata: c\n\n")]
    assert got == [True, True, False]


def test_drop_short_circuits_later_rules():
    eng = Engine([
        Rule("a", Match(seq=1), [Drop()]),
        Rule("b", Match(seq=1), [Rewrite("x", "y")]),
    ])
    ops, fired = eng.decide(frames(b"data: a\n\n")[0], CTX)
    assert ops == [Drop()]
    assert fired == ["a"]


def test_several_ops_from_one_rule():
    eng = Engine([Rule("r", Match(seq=1),
                       [Delay(500), Rewrite("a", "b"),
                        Inject("data: extra")])])
    ops, _ = eng.decide(frames(b"data: a\n\n")[0], CTX)
    assert len(ops) == 3


def test_reset_rearms():
    rule = Rule("r", Match(seq=1), [Cut()], limit=1)
    eng = Engine([rule])
    eng.decide(frames(b"data: a\n\n")[0], CTX)
    assert not rule.arm()
    eng.reset()
    assert rule.arm()
