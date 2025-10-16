"""The surface my other code is allowed to import.

I have two scripts on top of this now -- one that scores sessions in
a report directory, one that drives a replay out of a test harness --
and both reached straight into `sseint.session` and `sseint.rules`,
which is where the module layout changes every other release. Both
broke on a refactor I did not think touched anything.

So: one module, fully annotated, re-exporting the things worth
depending on. `docs/stability.md` says what the version number
promises about them. Everything not re-exported here is internal and
may move in a patch release, including under my own scripts.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence

from sseint.apply import Plan, plan
from sseint.compare import Comparison, compare
from sseint.decoders import by_name, for_content_type
from sseint.frame import Frame
from sseint.reassemble import describe, reassemble
from sseint.rulefile import RuleFileError
from sseint.rulefile import load as load_rules
from sseint.rules import (Context, Cut, Delay, Drop, Engine, Inject,
                          Match, Pause, Rewrite, Rule, SetField)
from sseint.session import Exchange, SessionWriter
from sseint.session import read as read_session
from sseint.timing import Stats, analyse

__all__ = [
    "Comparison", "Context", "Cut", "Delay", "Drop", "Engine",
    "Exchange", "Frame", "Inject", "Match", "Pause", "Plan",
    "Rewrite", "Rule", "RuleFileError", "SessionWriter", "SetField",
    "Stats", "analyse", "by_name", "compare", "decode", "describe",
    "for_content_type", "load_rules", "plan", "read_session",
    "reassemble",
]


def decode(chunks: Iterable[bytes], *,
           decoder: str = "sse") -> Sequence[Frame]:
    """Decode a complete recorded body into frames.

    The convenience nobody should have to write themselves: feed the
    chunks, flush at the end, get the frames. Timing comes from the
    clock at decode time, so this is for parsing, not for measuring.
    """
    dec = by_name(decoder)
    if dec is None:
        raise ValueError(f"unknown decoder {decoder!r}")
    out: list[Frame] = []
    for chunk in chunks:
        out.extend(dec.feed(chunk))
    out.extend(dec.close())
    return out
