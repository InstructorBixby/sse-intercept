from sseint.decoders.ndjson import NDJSONDecoder


def decode(chunks):
    d = NDJSONDecoder()
    out = []
    for c in chunks:
        out += d.feed(c)
    out += d.close()
    return out


def test_one_object_per_line():
    out = decode([b'{"a":1}\n{"a":2}\n'])
    assert [f.data for f in out] == ['{"a":1}', '{"a":2}']


def test_object_split_across_reads():
    out = decode([b'{"a":', b'1}\n'])
    assert [f.data for f in out] == ['{"a":1}']


def test_pretty_printed_object_is_held_and_reassembled():
    out = decode([b'{\n  "a": 1\n}\n'])
    assert len(out) == 1
    assert out[0].note is None


def test_final_line_without_newline():
    out = decode([b'{"a":1}'])
    assert out[0].note == "eof"


def test_garbage_is_surrendered_not_swallowed():
    out = decode([b'not json at all'])
    assert out[0].note in ("eof", "unparsed")
    assert out[0].data == "not json at all"


def test_blank_lines_are_not_frames():
    out = decode([b'\n\n{"a":1}\n'])
    assert len(out) == 1
