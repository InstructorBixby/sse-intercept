"""The decisions the proxy subcommand makes before anything listens.

Scope refusal is the one behaviour in this tool that must never
regress, so it is tested without binding a port or importing
mitmproxy.
"""
from __future__ import annotations

import io
from types import SimpleNamespace

import pytest

from sseint.proxy_cli import expand_hosts, resolve_scope, settings_for


def args(**kw):
    base = dict(allow_host=[], rules=None, record=None,
                no_redact=False, decoder=None, pause_budget=30,
                confdir="~/.mitmproxy", quiet=False, set=[],
                host="127.0.0.1", port=8080)
    base.update(kw)
    return SimpleNamespace(**base)


def test_plain_values_pass_through():
    assert expand_hosts(["a.test", "*.b.test"]) == ["a.test", "*.b.test"]


def test_at_file(tmp_path):
    path = tmp_path / "scope.txt"
    path.write_text("a.test\n# a comment\n\n*.b.test  # inline\n")
    assert expand_hosts([f"@{path}"]) == ["a.test", "*.b.test"]


def test_a_missing_scope_file_raises(tmp_path):
    with pytest.raises(OSError):
        expand_hosts([f"@{tmp_path / 'nope.txt'}"])


def test_empty_scope_refuses():
    err = io.StringIO()
    assert resolve_scope(args(), err=err) is None
    assert "empty scope" in err.getvalue()


def test_whitespace_only_scope_still_refuses():
    err = io.StringIO()
    assert resolve_scope(args(allow_host=["  ", ""]), err=err) is None


def test_a_missing_scope_file_refuses_rather_than_shrinking_scope(
        tmp_path):
    err = io.StringIO()
    got = resolve_scope(args(allow_host=["a.test",
                                         f"@{tmp_path / 'no.txt'}"]),
                        err=err)
    assert got is None


def test_rule_file_hosts_are_added(tmp_path):
    rules = tmp_path / "r.yaml"
    rules.write_text("allow_hosts: [from-file.test]\nrules: []\n")
    got = resolve_scope(args(allow_host=["a.test"], rules=str(rules)))
    assert got == ["a.test", "from-file.test"]


def test_a_bad_rule_file_refuses(tmp_path):
    rules = tmp_path / "r.yaml"
    rules.write_text("rules:\n  - {id: x, match: {nope: 1}}\n")
    err = io.StringIO()
    assert resolve_scope(args(allow_host=["a.test"],
                              rules=str(rules)), err=err) is None
    assert "nope" in err.getvalue()


def test_settings_passthrough_wins_over_nothing():
    got = settings_for(args(set=["stream_large_bodies=1m"]),
                       ["a.test"])
    assert got["stream_large_bodies"] == "1m"
    assert got["sseint_allow_hosts"] == "a.test"


def test_redact_default_is_on():
    assert settings_for(args(), ["a.test"])["sseint_redact"] is True
    assert settings_for(args(no_redact=True),
                        ["a.test"])["sseint_redact"] is False
