"""The surface is a promise I made to my own scripts, so it gets a test.

Not a test of behaviour -- every re-exported name is tested where it
lives -- but of the contract: the names exist, `__all__` matches what
is importable, and removing one has to be a deliberate act rather
than a refactor nobody noticed.
"""
from __future__ import annotations

import sseint.api as api


def test_all_names_are_importable():
    missing = [n for n in api.__all__ if not hasattr(api, n)]
    assert missing == []


def test_nothing_public_is_missing_from_all():
    public = {n for n in dir(api)
              if not n.startswith("_")
              and getattr(getattr(api, n), "__module__", "")
              .startswith("sseint")}
    assert public - set(api.__all__) == set()


def test_decode_convenience():
    frames = api.decode([b"data: a\n\n", b"data: b"])
    assert [f.data for f in frames] == ["a", "b"]


def test_decode_rejects_an_unknown_decoder():
    try:
        api.decode([b""], decoder="nope")
    except ValueError as exc:
        assert "nope" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_py_typed_ships():
    import importlib.resources as res
    assert res.files("sseint").joinpath("py.typed").is_file()
