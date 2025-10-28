from sseint.decoders.sse import SSEDecoder
from sseint.export import har
from sseint.session import Exchange


def exchange():
    ex = Exchange({"ex": 1, "host": "api.example.test",
                   "method": "POST", "path": "/v1/stream",
                   "status": "HTTP/1.1 200 OK", "decoder": "sse",
                   "request_headers": [["accept", "text/event-stream"]],
                   "response_headers": [["content-type",
                                         "text/event-stream"]]})
    d = SSEDecoder()
    ex.frames = d.feed(b"data: Hel\n\ndata: lo\n\n") + d.close()
    ex.frames[0].t = 0.4
    ex.frames[1].t = 1.4
    return ex


META = {"format": 1, "started_at": 1_700_000_000.0}


def test_shape():
    doc = har(META, [exchange()])
    assert doc["log"]["version"] == "1.2"
    assert len(doc["log"]["entries"]) == 1


def test_body_is_reassembled_and_said_to_be():
    doc = har(META, [exchange()])
    entry = doc["log"]["entries"][0]
    assert entry["response"]["content"]["text"] == "Hello"
    assert "REASSEMBLED" in doc["log"]["_sseint"]["note"]


def test_wait_is_time_to_first_frame():
    entry = har(META, [exchange()])["log"]["entries"][0]
    assert entry["timings"]["wait"] == 400
    assert entry["timings"]["receive"] == 1000


def test_frames_survive_in_the_extension_field():
    entry = har(META, [exchange()])["log"]["entries"][0]
    assert [f["seq"] for f in entry["_frames"]] == [1, 2]
    assert entry["_frames"][1]["at"] == 1.4


def test_status_code_is_extracted():
    entry = har(META, [exchange()])["log"]["entries"][0]
    assert entry["response"]["status"] == 200


def test_started_date_time_is_iso_with_a_zulu_suffix():
    entry = har(META, [exchange()])["log"]["entries"][0]
    assert entry["startedDateTime"].endswith("Z")
