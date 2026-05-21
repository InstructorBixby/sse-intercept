"""The surface other code is allowed to import.

One module, fully annotated, re-exporting the things worth depending
on. `docs/stability.md` says what the version number promises about
them. Everything not re-exported here is internal and may move in a
patch release -- which is the answer to "why did my import break", and
why `har`, the resume analysis and the invisible-codepoint helpers are
listed here rather than left in the modules that hold them.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence

from sseint.apply import Plan, plan
from sseint.compare import Comparison, compare
from sseint.decoders import by_name, for_content_type
from sseint.export import har
from sseint.frame import Frame
from sseint.reassemble import describe, reassemble
from sseint.resume import Reconnect
from sseint.resume import analyse as analyse_resume
from sseint.rulefile import RuleFileError
from sseint.rulefile import load as load_rules
from sseint.rules import (Context, Cut, Delay, Drop, Engine, Inject,
                          Match, Pause, Rewrite, Rule, SetField)
from sseint.session import Exchange, SessionWriter
from sseint.session import read as read_session
from sseint.timing import Stats, analyse, histogram
from sseint.visible import findings as invisible_findings
from sseint.visible import mark as mark_invisible

__all__ = [
    "Comparison", "Context", "Cut", "Delay", "Drop", "Engine",
    "Exchange", "Frame", "Inject", "Match", "Pause", "Plan",
    "Reconnect", "Rewrite", "Rule", "RuleFileError", "SessionWriter",
    "SetField", "Stats", "analyse", "analyse_resume", "by_name",
    "compare", "decode", "describe", "for_content_type", "har",
    "histogram", "invisible_findings", "load_rules", "mark_invisible",
    "plan", "read_session", "reassemble",
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
