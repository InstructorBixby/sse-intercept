from sseint.apply import plan
from sseint.decoders.sse import SSEDecoder
from sseint.rules import Cut, Delay, Drop, Inject, Pause, Rewrite, SetField


def one(raw: bytes):
    d = SSEDecoder()
    return (d.feed(raw) + d.close())[0]


def test_no_ops_emits_the_original_bytes():
    f = one(b"data: a\r\n\r\n")
    assert plan(f, []).emit == [b"data: a\r\n\r\n"]


def test_drop_emits_nothing():
    assert plan(one(b"data: a\n\n"), [Drop()]).emit == []


def test_delays_add():
    p = plan(one(b"data: a\n\n"), [Delay(1500), Delay(500)])
    assert p.delay_ms == 2000


def test_rewrite_reencodes():
    p = plan(one(b"data: hello\n\n"), [Rewrite("hello", "goodbye")])
    assert p.emit == [b"data: goodbye\r\n\r\n"]
    assert p.changed


def test_rewrite_that_matches_nothing_is_recorded():
    p = plan(one(b"data: hello\n\n"), [Rewrite("nope", "x")])
    assert not p.changed
    assert p.notes and "matched nothing" in p.notes[0]


def test_regex_rewrite():
    p = plan(one(b"data: tok-41\n\n"),
             [Rewrite(r"tok-\d+", "tok-0", regex=True)])
    assert p.emit == [b"data: tok-0\r\n\r\n"]


def test_set_field_adds_when_absent():
    p = plan(one(b"data: a\n\n"), [SetField("event", "token")])
    assert p.emit == [b"data: a\r\nevent: token\r\n\r\n"]


def test_inject_before_survives_a_drop():
    p = plan(one(b"data: a\n\n"),
             [Inject("data: substitute", where="before"), Drop()])
    assert p.emit == [b"data: substitute\r\n\r\n"]


def test_inject_after():
    p = plan(one(b"data: a\n\n"), [Inject("data: extra")])
    assert p.emit == [b"data: a\r\n\r\n", b"data: extra\r\n\r\n"]


def test_pause_is_a_flag_not_a_sleep():
    p = plan(one(b"data: a\n\n"), [Pause()])
    assert p.pause and p.delay_ms == 0


def test_cut_discards_the_queue():
    p = plan(one(b"data: a\n\n"), [Cut()])
    assert p.emit == []
    assert p.cut
