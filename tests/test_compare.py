from sseint.compare import compare, normalise


def test_identical():
    assert compare("hello", "hello").same


def test_whitespace_is_not_a_difference():
    assert compare("hello  world\r\n", "hello world\n").same


def test_a_real_difference_is_reported():
    c = compare("here is a link: http://example.test",
                "here is a link: [redacted]")
    assert not c.same
    assert any("redacted" in line for line in c.diff)
    assert "differ" in c.report()


def test_report_when_equivalent_says_so():
    assert "equivalent" in compare("a", "a ").report()


def test_normalise_strips_trailing_space_per_line():
    assert normalise("a   \nb\t\n") == "a\nb"
