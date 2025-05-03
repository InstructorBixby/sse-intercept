import pytest

from sseint import rules as R
from sseint.rulefile import RuleFileError, load


def write(tmp_path, text):
    p = tmp_path / "rules.yaml"
    p.write_text(text)
    return p


def test_minimal(tmp_path):
    hosts, eng = load(write(tmp_path, """
    allow_hosts: [api.example.test]
    rules:
      - id: drop-second
        match: {seq: 2}
        action: drop
    """))
    assert hosts == ["api.example.test"]
    assert eng.rules[0].id == "drop-second"
    assert eng.rules[0].ops == [R.Drop()]


def test_several_actions_and_a_limit(tmp_path):
    _, eng = load(write(tmp_path, """
    rules:
      - id: slow-and-mangle
        match: {data_contains: token}
        actions:
          - delay: {s: 2.5}
          - rewrite: {find: token, replace: ekot}
        limit: 1
    """))
    rule = eng.rules[0]
    assert rule.ops == [R.Delay(2500), R.Rewrite("token", "ekot", False)]
    assert rule.limit == 1


def test_unknown_match_key_is_an_error(tmp_path):
    with pytest.raises(RuleFileError) as exc:
        load(write(tmp_path, """
        rules:
          - id: typo
            match: {data_contain: x}
            action: drop
        """))
    assert "data_contain" in str(exc.value)


def test_unknown_action_is_an_error(tmp_path):
    with pytest.raises(RuleFileError):
        load(write(tmp_path, """
        rules:
          - {id: x, match: {seq: 1}, action: explode}
        """))


def test_duplicate_ids_are_an_error(tmp_path):
    with pytest.raises(RuleFileError):
        load(write(tmp_path, """
        rules:
          - {id: same, match: {seq: 1}, action: drop}
          - {id: same, match: {seq: 2}, action: drop}
        """))


def test_inject_shorthand(tmp_path):
    _, eng = load(write(tmp_path, """
    rules:
      - id: add
        match: {seq: 1}
        action: {inject: "data: hello"}
    """))
    assert eng.rules[0].ops == [R.Inject("data: hello", "after")]
