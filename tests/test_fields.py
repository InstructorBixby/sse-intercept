import sseframe


def parse(raw):
    block, rest = sseframe.split_block(raw)
    assert block is not None, rest
    return sseframe.parse_block(block)[0]


def test_event_and_id():
    f = parse(b"event: token\nid: 7\ndata: hi\n\n")
    assert sseframe.event_of(f) == "token"
    assert sseframe.id_of(f) == "7"
    assert sseframe.data_of(f) == "hi"


def test_retry_is_milliseconds():
    assert sseframe.retry_of(parse(b"retry: 3000\n\n")) == 3000


def test_retry_non_integer_is_ignored():
    assert sseframe.retry_of(parse(b"retry: soon\n\n")) is None


def test_done_sentinel():
    assert sseframe.is_done(parse(b"data: [DONE]\n\n"))
    assert not sseframe.is_done(parse(b"data: not done\n\n"))


def test_first_wins_for_single_valued_fields():
    f = parse(b"id: 1\nid: 2\n\n")
    assert sseframe.id_of(f) == "1"
