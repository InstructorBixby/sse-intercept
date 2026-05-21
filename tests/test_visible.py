from sseint import visible


def test_plain_text_is_untouched():
    assert visible.mark("hello world") == "hello world"
    assert visible.clean("hello world")


def test_zero_width_space():
    assert visible.mark("a\u200bb") == "a<ZWSP>b"


def test_bidi_override():
    assert visible.mark("x\u202ey") == "x<RLO>y"


def test_tag_block_shows_the_ascii_offset():
    # U+E0041 is the tag form of "A"; the offset is what makes a
    # smuggled instruction readable in a report.
    assert visible.mark("\U000e0041") == "<TAG+0041>"


def test_soft_hyphen_and_bom():
    assert visible.mark("a\u00adb\ufeff") == "a<SHY>b<BOM>"


def test_variation_selector():
    assert "<VS>" in visible.mark("a\ufe0f")


def test_private_use_area():
    assert visible.mark("\ue000") == "<PUA>"


def test_tabs_and_newlines_are_left_alone():
    assert visible.mark("a\tb\nc") == "a\tb\nc"


def test_findings_report_offsets():
    got = visible.findings("ab\u200bc")
    assert got == [(2, "U+200B", "ZWSP")]


def test_clean_is_false_when_something_is_hiding():
    assert not visible.clean("a\u200bb")
