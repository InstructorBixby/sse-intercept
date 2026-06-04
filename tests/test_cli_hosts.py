import pytest

from sseint.cli import expand_hosts


def test_plain_values_pass_through():
    assert expand_hosts(["a.test", "*.b.test"]) == ["a.test", "*.b.test"]


def test_at_file(tmp_path):
    path = tmp_path / "scope.txt"
    path.write_text("a.test\n# a comment\n\n*.b.test  # inline\n")
    assert expand_hosts([f"@{path}"]) == ["a.test", "*.b.test"]


def test_file_and_flags_combine(tmp_path):
    path = tmp_path / "scope.txt"
    path.write_text("a.test\n")
    assert expand_hosts(["z.test", f"@{path}"]) == ["z.test", "a.test"]


def test_a_missing_file_raises_rather_than_silently_emptying_scope(
        tmp_path):
    with pytest.raises(OSError):
        expand_hosts([f"@{tmp_path / 'nope.txt'}"])
