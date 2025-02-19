"""The unit everything else deals in."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Frame:
    """One decoded frame, with where and when it came from.

    `raw` is kept because the decoded view is lossy by design: a
    report needs the bytes, and a rewrite rule needs something to put
    back on the wire.
    """

    seq: int
    t: float                      # seconds since the first byte of body
    kind: str                     # event | comment | line | chunk
    raw: bytes
    fields: list[tuple[str, str]] = field(default_factory=list)
    comments: list[str] = field(default_factory=list)
    note: str | None = None       # eof, injected, rewritten, ...

    @property
    def data(self) -> str:
        return "\n".join(v for k, v in self.fields if k == "data")

    @property
    def event(self) -> str | None:
        return self.first("event")

    @property
    def id(self) -> str | None:
        return self.first("id")

    def first(self, name: str) -> str | None:
        for k, v in self.fields:
            if k == name:
                return v
        return None

    def summary(self, width: int = 60) -> str:
        body = self.data if self.fields else " ".join(self.comments)
        body = body.replace("\n", "\\n")
        if len(body) > width:
            body = body[: width - 1] + "~"
        return body
