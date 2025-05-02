"""Ops -> a plan the relay can execute.

Kept separate from both the engine and the relay because this is where
the fiddly semantics live and they deserve tests of their own: what
happens when a rule both rewrites and injects, what `before` means
when the frame is also dropped, whether two delays add.

Decisions encoded here:

- delays add. Two rules that each delay by 2s delay by 4s; a rule that
  wants the maximum can say so with one rule.
- `inject before` emits even if the frame itself is dropped. That is
  the substitution case and it is the common one.
- a cut discards everything queued after it, because there is no
  connection left to write to.
- a rewrite that produces no change is still recorded. A rule that
  silently matched nothing is how a test accidentally passes.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from sseint import rules as R
from sseint.frame import Frame
from sseint.wire import encode, encode_text


@dataclass
class Plan:
    emit: list[bytes] = field(default_factory=list)
    delay_ms: int = 0
    pause: bool = False
    cut: bool = False
    changed: bool = False
    notes: list[str] = field(default_factory=list)


def plan(frame: Frame, ops) -> Plan:
    p = Plan()
    before: list[bytes] = []
    after: list[bytes] = []
    dropped = False
    fields = list(frame.fields)
    comments = list(frame.comments)

    for op in ops:
        if isinstance(op, R.Drop):
            dropped = True
        elif isinstance(op, R.Delay):
            p.delay_ms += op.ms
        elif isinstance(op, R.Pause):
            p.pause = True
        elif isinstance(op, R.Cut):
            p.cut = True
        elif isinstance(op, R.Inject):
            (before if op.where == "before" else after).append(
                encode_text(op.text))
        elif isinstance(op, R.Rewrite):
            fields, comments, hit = _rewrite(fields, comments, op)
            p.changed = p.changed or hit
            if not hit:
                p.notes.append(f"rewrite {op.find!r} matched nothing")
        elif isinstance(op, R.SetField):
            fields = _set_field(fields, op.name, op.value)
            p.changed = True
        else:
            raise TypeError(f"unknown op {op!r}")

    p.emit += before
    if not dropped:
        if p.changed:
            rewritten = Frame(seq=frame.seq, t=frame.t, kind=frame.kind,
                              raw=frame.raw, fields=fields,
                              comments=comments, note="rewritten")
            p.emit.append(encode(rewritten))
        else:
            # Unmodified frames go back as the exact bytes that
            # arrived. Re-encoding a frame nobody asked to change is
            # how a proxy ends up being the thing under test.
            p.emit.append(frame.raw + b"\r\n\r\n")
    p.emit += after
    if p.cut:
        p.emit = p.emit[:1] if before else []
    return p


def _rewrite(fields, comments, op: R.Rewrite):
    hit = False
    out = []
    for name, value in fields:
        new = _sub(value, op)
        hit = hit or new != value
        out.append((name, new))
    newcomments = []
    for c in comments:
        new = _sub(c, op)
        hit = hit or new != c
        newcomments.append(new)
    return out, newcomments, hit


def _sub(value: str, op: R.Rewrite) -> str:
    if op.regex:
        return re.sub(op.find, op.replace, value)
    return value.replace(op.find, op.replace)


def _set_field(fields, name, value):
    out = []
    seen = False
    for k, v in fields:
        if k == name and not seen:
            out.append((k, value))
            seen = True
        else:
            out.append((k, v))
    if not seen:
        out.append((name, value))
    return out
