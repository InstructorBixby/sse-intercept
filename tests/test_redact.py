from sseint.redact import header_value, headers


def test_bearer_token_length_survives_the_value():
    got = header_value("Authorization", "Bearer abcdef123456")
    assert got == "Bearer <redacted:12>"


def test_unknown_header_is_untouched():
    assert header_value("accept", "text/event-stream") == \
        "text/event-stream"


def test_api_key_keeps_a_short_prefix():
    got = header_value("x-api-key", "sk-livekey-0123456789")
    assert got.startswith("sk-l")
    assert "0123456789" not in got


def test_cookie_is_redacted():
    assert "<redacted" in header_value("Cookie", "session=deadbeef")


def test_case_insensitive():
    assert "<redacted" in header_value("AUTHORIZATION", "Bearer x")


def test_headers_preserves_order_and_duplicates():
    pairs = [("accept", "a"), ("cookie", "x"), ("accept", "b")]
    got = headers(pairs)
    assert [k for k, _ in got] == ["accept", "cookie", "accept"]
    assert got[0][1] == "a" and got[2][1] == "b"
