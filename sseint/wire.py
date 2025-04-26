"""Frame -> bytes.

Needed the moment a rule can change a frame: whatever goes back on the
wire has to be a valid frame, not the original bytes with a substring
swapped. The two cases that bite:

- a `data` value containing a newline is several `data:` lines, not one
  line with an embedded newline, which would terminate the frame early
  and hand the client two frames where there was one;
- a comment frame is `:text`, with no field name, and encoding it as a
  field produces a frame with the name "" that some clients drop and
  others treat as `message`.
"""
from __future__ import annotations

from sseint.frame import Frame

CRLF = b"\r\n"


def encode(frame: Frame) -> bytes:
    """Serialise one frame, terminator included."""
    lines: list[str] = []
    for c in frame.comments:
        lines.append(f":{c}")
    for name, value in frame.fields:
        if name == "data" and "\n" in value:
            lines += [f"data: {part}" for part in value.split("\n")]
        else:
            lines.append(f"{name}: {value}")
    if not lines:
        return CRLF
    body = CRLF.join(line.encode("utf-8") for line in lines)
    return body + CRLF + CRLF


def encode_text(text: str) -> bytes:
    """Serialise a hand-written frame from a rule file.

    The text is taken as frame lines verbatim, so a rule can inject an
    `event:` name or a bare comment without a dataclass in the way. A
    trailing blank line is added if absent.
    """
    text = text.replace("\r\n", "\n").rstrip("\n")
    body = CRLF.join(line.encode("utf-8") for line in text.split("\n"))
    return body + CRLF + CRLF
