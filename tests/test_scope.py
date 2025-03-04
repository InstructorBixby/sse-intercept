from sseint.scope import Scope


def test_empty_scope_allows_nothing():
    s = Scope([])
    assert not s
    assert not s.allows("example.test")


def test_exact_host():
    s = Scope(["api.example.test"])
    assert s.allows("api.example.test")
    assert not s.allows("evil.example.test")


def test_glob():
    s = Scope(["*.example.test"])
    assert s.allows("api.example.test")
    assert not s.allows("example.test")


def test_case_insensitive():
    assert Scope(["API.Example.Test"]).allows("api.example.test")


def test_none_host_is_refused():
    assert not Scope(["*"]).allows(None)
