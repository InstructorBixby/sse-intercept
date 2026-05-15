"""What the viewer shows, with no curses in it.

The terminal half of a TUI is untestable in any way that is worth the
effort, so everything that decides *what* is on screen lives here and
gets tests: filtering, the window of visible rows, the selection, and
the detail pane. `view.py` is then a thin translation of this into
curses calls and is allowed to be dull.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from sseint.reassemble import reassemble
from sseint.timing import analyse

MARKS = {"comment": ":", "event": "#", "line": ".", "chunk": "~"}


@dataclass
class Filter:
    text: str = ""
    regex: bool = False
    kinds: set = field(default_factory=set)
    touched_only: bool = False     # frames a rule acted on

    def test(self, frame, ops) -> bool:
        if self.kinds and frame.kind not in self.kinds:
            return False
        if self.touched_only and not ops:
            return False
        if not self.text:
            return True
        hay = frame.data or " ".join(frame.comments)
        if self.regex:
            try:
                return bool(re.search(self.text, hay))
            except re.error:
                return False
        return self.text.lower() in hay.lower()


class ViewModel:
    """Follow mode and a filter used to fight each other.

    Typing a filter while following the tail of a live session would
    re-pin the view to the bottom on every keystroke, so the frame you
    were trying to look at left the screen as you typed. Follow is now
    cancelled by filtering as well as by moving, and `visible()` keeps
    whatever is selected on screen rather than deciding where the
    window goes from scratch.
    """

    def __init__(self, exchanges, height: int = 20):
        self.exchanges = list(exchanges)
        self.index = 0
        self.selected = 0
        self.top = 0
        self.height = height
        self._filter = Filter()
        self.follow = True

    @property
    def filter(self):
        return self._filter

    @filter.setter
    def filter(self, value):
        self._filter = value
        self.follow = False

    def set_filter(self, **changes):
        for key, value in changes.items():
            setattr(self._filter, key, value)
        self.follow = False

    @property
    def exchange(self):
        return self.exchanges[self.index] if self.exchanges else None

    def next_exchange(self):
        if self.exchanges:
            self.index = (self.index + 1) % len(self.exchanges)
            self.selected = self.top = 0

    def prev_exchange(self):
        if self.exchanges:
            self.index = (self.index - 1) % len(self.exchanges)
            self.selected = self.top = 0

    @property
    def rows(self):
        ex = self.exchange
        if ex is None:
            return []
        out = []
        for f in ex.frames:
            ops = ex.ops.get(f.seq, [])
            if self._filter.test(f, ops):
                out.append((f, ops))
        return out

    def visible(self):
        rows = self.rows
        if self.follow and len(rows) > self.height:
            self.top = len(rows) - self.height
            self.selected = len(rows) - 1
        self.selected = max(0, min(self.selected, max(0, len(rows) - 1)))
        if self.selected < self.top:
            self.top = self.selected
        elif self.selected >= self.top + self.height:
            self.top = self.selected - self.height + 1
        self.top = max(0, min(self.top, max(0, len(rows) - self.height)))
        return rows[self.top:self.top + self.height]

    def move(self, delta: int):
        rows = self.rows
        if not rows:
            return
        self.follow = False
        self.selected = max(0, min(len(rows) - 1, self.selected + delta))
        if self.selected < self.top:
            self.top = self.selected
        elif self.selected >= self.top + self.height:
            self.top = self.selected - self.height + 1

    @property
    def current(self):
        rows = self.rows
        if not rows:
            return None
        return rows[min(self.selected, len(rows) - 1)]

    def line(self, frame, ops, width: int = 70) -> str:
        mark = MARKS.get(frame.kind, "?")
        tag = f" [{','.join(ops)}]" if ops else ""
        return (f"{mark}{frame.seq:<4} +{frame.t:7.3f}s  "
                f"{frame.summary(width)}{tag}")

    def detail(self) -> list[str]:
        row = self.current
        if row is None:
            return ["no frames"]
        frame, ops = row
        out = [f"frame {frame.seq}  kind={frame.kind}  "
               f"t=+{frame.t:.3f}s"]
        if ops:
            out.append(f"rules: {', '.join(ops)}")
        if frame.note:
            out.append(f"note: {frame.note}")
        for name, value in frame.fields:
            for i, part in enumerate(value.split("\n")):
                out.append(f"{name if i == 0 else '':>8}: {part}")
        for c in frame.comments:
            out.append(f"       :{c}")
        return out

    def status(self) -> str:
        ex = self.exchange
        if ex is None:
            return "no exchanges"
        rows = len(self.rows)
        total = len(ex.frames)
        bits = [f"[{self.index + 1}/{len(self.exchanges)}]",
                f"{ex.method} {ex.host}{ex.path}",
                f"{rows}/{total} frames"]
        if self._filter.text:
            bits.append(f"/{self._filter.text}")
        if self._filter.touched_only:
            bits.append("touched")
        bits.append("follow" if self.follow else "paged")
        return "  ".join(bits)

    def summary(self) -> list[str]:
        ex = self.exchange
        if ex is None:
            return []
        st = analyse(ex.frames, added=ex.added_ms)
        return st.lines()

    def reassembled(self, mode="data") -> str:
        ex = self.exchange
        return reassemble(ex.frames, mode) if ex else ""
