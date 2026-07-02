from sseint.decoders.ndjson import NDJSONDecoder


def test_held_text_is_surrendered_at_the_cap():
    d = NDJSONDecoder(max_held_bytes=32)
    frames = d.feed(b"not json\n" * 10)
    assert any(f.note == "unparsed" for f in frames)


def test_holding_restarts_after_a_surrender():
    d = NDJSONDecoder(max_held_bytes=16)
    d.feed(b"nope\nnope\nnope\nnope\n")
    frames = d.feed(b'{"a":1}\n')
    assert [f.note for f in frames][-1] is None


def test_a_pretty_printed_object_under_the_cap_still_reassembles():
    d = NDJSONDecoder()
    frames = d.feed(b'{\n  "a": 1\n}\n')
    assert len(frames) == 1 and frames[0].note is None
