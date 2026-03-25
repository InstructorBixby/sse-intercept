"""Plugin loading, without installing anything.

`entry_points` is monkeypatched: installing a package per test case is
slower than the feature is interesting.
"""
from __future__ import annotations

from dataclasses import dataclass

from sseint import decoders


@dataclass
class FakeEP:
    name: str
    obj: object

    def load(self):
        if isinstance(self.obj, Exception):
            raise self.obj
        return self.obj


class Good:
    name = "private"
    content_types = ("application/vnd.example.stream",)

    def feed(self, chunk):
        return []

    def close(self):
        return []


class Shadow(Good):
    name = "sse"


class NotADecoder:
    name = "broken"
    content_types = ()


def patch(monkeypatch, eps):
    monkeypatch.setattr(decoders, "entry_points",
                        lambda group=None: eps)


def test_a_plugin_is_registered(monkeypatch):
    patch(monkeypatch, [FakeEP("private", Good)])
    reg = decoders.registry(warn=False)
    assert Good in reg


def test_a_builtin_wins_and_the_shadow_is_reported(monkeypatch, capsys):
    patch(monkeypatch, [FakeEP("sse", Shadow)])
    reg = decoders.registry()
    assert Shadow not in reg
    assert "shadows a built-in" in capsys.readouterr().err


def test_an_import_error_is_survivable(monkeypatch, capsys):
    patch(monkeypatch, [FakeEP("bad", ImportError("no module"))])
    reg = decoders.registry()
    assert reg == decoders.BUILTIN
    assert "failed to load" in capsys.readouterr().err


def test_something_that_is_not_a_decoder_is_refused(monkeypatch):
    patch(monkeypatch, [FakeEP("broken", NotADecoder)])
    assert NotADecoder not in decoders.registry(warn=False)
