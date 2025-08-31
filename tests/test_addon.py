"""The addon, exercised with a stub flow.

mitmproxy's own objects are perfectly testable, but constructing a
full flow drags in more of the library than this needs. What matters
is the contract: `responseheaders` assigns a callable to
`flow.response.stream`, and that callable returns the bytes the client
should get.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from sseint.addon import StreamTap
from sseint.rules import Drop, Engine, Match, Rule


class Headers(dict):
    def get(self, key, default=None):
        return dict.get(self, key.lower(), default)

    def items(self, multi=False):
        return list(dict.items(self))

    def __contains__(self, key):
        return dict.__contains__(self, key.lower())

    def __delitem__(self, key):
        dict.__delitem__(self, key.lower())


def flow(ctype="text/event-stream", host="api.example.test",
         path="/v1/stream", extra=None):
    headers = Headers({"content-type": ctype})
    headers.update({k.lower(): v for k, v in (extra or {}).items()})
    return SimpleNamespace(
        request=SimpleNamespace(pretty_host=host, path=path,
                                method="POST"),
        response=SimpleNamespace(status_code=200, reason="OK",
                                 headers=headers, stream=None))


@pytest.fixture
def tap():
    t = StreamTap()
    t.scope.patterns = ["api.example.test"]
    t.console.quiet = True
    return t


def test_non_streaming_response_is_left_alone(tap):
    f = flow(ctype="application/json")
    tap.responseheaders(f)
    assert f.response.stream is None


def test_streaming_response_gets_a_streamer(tap):
    f = flow()
    tap.responseheaders(f)
    assert callable(f.response.stream)


def test_streamer_passes_bytes_through_when_observing(tap):
    f = flow()
    tap.responseheaders(f)
    assert f.response.stream(b"data: a\n\n") == b"data: a\n\n"
    assert f.response.stream(b"") == b""


def test_streamer_applies_rules(tap):
    tap.engine = Engine([Rule("r", Match(seq=1), [Drop()])])
    f = flow()
    tap.responseheaders(f)
    out = f.response.stream(b"data: a\n\ndata: b\n\n")
    assert out == b"data: b\r\n\r\n"


def test_empty_chunk_flushes_the_decoder(tap):
    tap.engine = Engine([Rule("r", Match(seq=99), [Drop()])])
    f = flow()
    tap.responseheaders(f)
    f.response.stream(b"data: a\n\ndata: last")
    assert f.response.stream(b"") == b"data: last\r\n\r\n"


def test_content_length_is_removed_when_rules_are_armed(tap):
    tap.engine = Engine([Rule("r", Match(seq=1), [Drop()])])
    f = flow(extra={"content-length": "40"})
    tap.responseheaders(f)
    assert "content-length" not in f.response.headers


def test_out_of_scope_request_is_answered_without_an_upstream(tap):
    import mitmproxy.http as mhttp

    f = flow(host="elsewhere.test")
    f.response = None
    tap.requestheaders(f)
    assert isinstance(f.response, mhttp.Response)
    assert f.response.status_code == 403
