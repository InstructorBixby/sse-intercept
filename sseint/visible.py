"""Render invisible codepoints visibly.

A frame whose data contains a zero-width space, a bidi override, or a
codepoint from the Unicode Tags block looks in the frame view exactly
like a frame that does not. That is the entire problem: the transcript
of the test is unreadable in precisely the case where the transcript
is the finding.

So `--visible` substitutes a named marker for every codepoint that
renders as nothing or renders as something other than itself. The
result is not meant to be copied back onto the wire; it is meant to be
legible in a terminal and in a report.

Scope: this is the frame-level version and deliberately shallow. The
thorough treatment -- confusable skeletons, mixed-script detection,
normalisation differences, per-path allowlists -- is glyphstop's job,
and if glyphstop is installed this module hands off to it rather than
keeping a second, worse table. Without it, the built-in table below
covers the classes that have actually turned up in a stream.
"""
from __future__ import annotations

import unicodedata

try:                                    # optional, better if present
    from glyphstop.explain import mark_line as _glyphstop_mark
except ImportError:                     # pragma: no cover
    _glyphstop_mark = None

NAMED = {
    0x0000: "NUL",
    0x00AD: "SHY",        # soft hyphen
    0x061C: "ALM",        # arabic letter mark
    0x180E: "MVS",        # mongolian vowel separator
    0x200B: "ZWSP",
    0x200C: "ZWNJ",
    0x200D: "ZWJ",
    0x200E: "LRM",
    0x200F: "RLM",
    0x202A: "LRE",
    0x202B: "RLE",
    0x202C: "PDF",
    0x202D: "LRO",
    0x202E: "RLO",
    0x2060: "WJ",         # word joiner
    0x2066: "LRI",
    0x2067: "RLI",
    0x2068: "FSI",
    0x2069: "PDI",
    0xFEFF: "BOM",
}

RANGES = [
    (0xE0000, 0xE007F, "TAG"),        # Unicode Tags block
    (0xFE00, 0xFE0F, "VS"),           # variation selectors
    (0xE0100, 0xE01EF, "VS"),         # variation selectors supplement
    (0xE000, 0xF8FF, "PUA"),
    (0xF0000, 0xFFFFD, "PUA"),
    (0x100000, 0x10FFFD, "PUA"),
]


def classify(ch: str) -> str | None:
    """A short name if this codepoint is worth showing, else None."""
    cp = ord(ch)
    if cp in NAMED:
        return NAMED[cp]
    for lo, hi, label in RANGES:
        if lo <= cp <= hi:
            return f"{label}+{cp - lo:04X}" if label == "TAG" else label
    cat = unicodedata.category(ch)
    if cat == "Cf":
        return "Cf"
    if cat == "Cc" and ch not in "\t\n\r":
        return "Cc"
    if cat == "Cn":
        return "UNASSIGNED"
    if cat == "Co":
        return "PUA"
    return None


def findings(text: str) -> list[tuple[int, str, str]]:
    """(offset, codepoint as U+XXXX, short name) for each hit."""
    out = []
    for i, ch in enumerate(text):
        name = classify(ch)
        if name is not None:
            out.append((i, f"U+{ord(ch):04X}", name))
    return out


def mark(text: str) -> str:
    """Substitute a marker for every invisible codepoint."""
    if _glyphstop_mark is not None:
        return _glyphstop_mark(text)
    out = []
    for ch in text:
        name = classify(ch)
        out.append(f"<{name}>" if name is not None else ch)
    return "".join(out)


def clean(text: str) -> bool:
    return not findings(text)
