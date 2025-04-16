"""Interception rules.

This is the point of the tool. Everything else is plumbing to get a
frame in front of a decision.

The engine is pure: `(frame, context) -> list[Op]`. It does no I/O,
does not sleep, and does not touch a socket, which is what makes the
interesting cases testable without a server. The relay executes the
ops it is handed.

Ops, and why each one is here:

- `drop`    -- the client never sees the frame. Tests whether a client
               assumes contiguous ids, and whether a missing final
               frame hangs it.
- `delay`   -- the frame arrives late. The direct test for read-timeout
               handling, which is where streaming clients are weakest.
- `rewrite` -- frame content changes mid-stream. The only way to ask
               what a client does when frame 40 contradicts frame 39.
- `inject`  -- a frame the server never sent. Tests whether anything
               downstream distinguishes server content from content
               that merely arrived on the connection.
- `pause`   -- hold the stream until released, for doing something
               else while it is open.
- `cut`     -- close the response mid-stream. Tests the incomplete
               case, which almost nothing handles.
"""
from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field

from sseint.frame import Frame


# --- ops ----------------------------------------------------------
@dataclass(frozen=True)
class Drop:
    pass


@dataclass(frozen=True)
class Delay:
    ms: int


@dataclass(frozen=True)
class Rewrite:
    find: str
    replace: str
    regex: bool = False


@dataclass(frozen=True)
class SetField:
    name: str
    value: str


@dataclass(frozen=True)
class Inject:
    text: str
    where: str = "after"        # before | after


@dataclass(frozen=True)
class Pause:
    pass


@dataclass(frozen=True)
class Cut:
    pass


# --- matching -----------------------------------------------------
@dataclass
class Match:
    host: str | None = None          # glob
    path: str | None = None          # glob
    seq: int | None = None
    seq_from: int | None = None
    seq_to: int | None = None
    kind: str | None = None
    event: str | None = None
    data_contains: str | None = None
    data_matches: str | None = None  # regex

    def __post_init__(self):
        self._rx = re.compile(self.data_matches) if self.data_matches \
            else None

    def test(self, frame: Frame, ctx: "Context") -> bool:
        if self.host and not fnmatch.fnmatch(ctx.host.lower(),
                                             self.host.lower()):
            return False
        if self.path and not fnmatch.fnmatch(ctx.path, self.path):
            return False
        if self.seq is not None and frame.seq != self.seq:
            return False
        if self.seq_from is not None and frame.seq < self.seq_from:
            return False
        if self.seq_to is not None and frame.seq > self.seq_to:
            return False
        if self.kind and frame.kind != self.kind:
            return False
        if self.event is not None and frame.event != self.event:
            return False
        if self.data_contains and self.data_contains not in frame.data:
            return False
        if self._rx and not self._rx.search(frame.data):
            return False
        return True


@dataclass
class Context:
    host: str = ""
    path: str = ""


@dataclass
class Rule:
    id: str
    match: Match
    ops: list = field(default_factory=list)
    limit: int | None = None
    fired: int = 0

    def arm(self) -> bool:
        return self.limit is None or self.fired < self.limit


class Engine:

    def __init__(self, rules=()):
        self.rules = list(rules)

    def decide(self, frame: Frame, ctx: Context):
        """Return (ops, rule_ids) for one frame."""
        ops = []
        fired = []
        for rule in self.rules:
            if not rule.arm():
                continue
            if not rule.match.test(frame, ctx):
                continue
            rule.fired += 1
            fired.append(rule.id)
            ops += rule.ops
            if any(isinstance(o, (Drop, Cut)) for o in rule.ops):
                # Nothing after a drop or a cut can apply to this
                # frame; stopping here keeps the ops list honest.
                break
        return ops, fired

    def reset(self):
        for rule in self.rules:
            rule.fired = 0

    def __bool__(self):
        return bool(self.rules)
