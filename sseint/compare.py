"""Streamed against non-streamed.

The same request, once with the streaming flag and once without,
should produce the same message. When it does not, the usual cause is
a control that runs on a complete response and cannot run on a stream:
a filter, a redaction pass, a safety check, a markdown sanitiser. The
streamed path skips it, and the difference is the finding.

This needs no injection and no model behaviour to demonstrate, which
makes it the cheapest useful test in the tool and the first thing to
run against a new endpoint.

The comparison is deliberately dumb: normalise whitespace, diff, and
report. Anything cleverer starts making judgements about which
differences matter, and that judgement belongs to whoever reads the
report.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

WS = re.compile(r"[ \t]+")


def normalise(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = "\n".join(WS.sub(" ", line).rstrip()
                     for line in text.split("\n"))
    return text.strip()


@dataclass
class Comparison:
    streamed: str
    whole: str
    diff: list[str] = field(default_factory=list)

    @property
    def same(self) -> bool:
        return not self.diff

    def report(self) -> str:
        if self.same:
            return ("streamed and non-streamed responses are "
                    "equivalent after whitespace normalisation")
        lines = [
            "streamed and non-streamed responses differ",
            f"  streamed:     {len(self.streamed)} chars",
            f"  non-streamed: {len(self.whole)} chars",
            "",
        ]
        return "\n".join(lines + self.diff)


def compare(streamed: str, whole: str, context: int = 2) -> Comparison:
    a, b = normalise(streamed), normalise(whole)
    if a == b:
        return Comparison(streamed=a, whole=b)
    diff = list(difflib.unified_diff(
        a.split("\n"), b.split("\n"),
        fromfile="streamed", tofile="non-streamed",
        n=context, lineterm=""))
    return Comparison(streamed=a, whole=b, diff=diff)
