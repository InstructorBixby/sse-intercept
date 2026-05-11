"""Put a stream back together.

Two reasons this matters more than it sounds.

First, a report needs the message, not 300 frames of it.

Second, and the actual motivation: the reassembled streamed response
and the non-streamed response to the same request are supposed to be
the same message. When they are not -- and they are not, more often
than anyone expects -- the difference is usually a control that runs
on the complete response and cannot run on a stream. That is a finding
that needs no injection to demonstrate, and this is the cheapest way
to find it.

Three modes:

- `data`: concatenate every `data:` payload. Correct for a stream
  whose frames are text fragments.
- `lines`: join with a newline, per the spec's own reading of
  multi-line data.
- `json:<path>`: parse each frame's data as JSON and concatenate the
  value at a dotted path, which is how every delta-shaped chat stream
  is laid out. Numeric components index a list.
"""
from __future__ import annotations

import json

from sseint.decoders.sse import DONE_SENTINEL
from sseint.frame import Frame


def reassemble(frames: list[Frame], mode: str = "data") -> str:
    if mode == "data":
        return "".join(_payloads(frames))
    if mode == "lines":
        return "\n".join(_payloads(frames))
    if mode.startswith("json:"):
        return _json_path(frames, mode[len("json:"):])
    raise ValueError(f"unknown reassembly mode {mode!r}")


def _payloads(frames):
    for f in frames:
        if f.kind == "comment":
            continue
        data = f.data
        if data.strip() == DONE_SENTINEL:
            continue
        yield data


def _json_path(frames, path: str) -> str:
    parts = [p for p in path.split(".") if p]
    out = []
    for data in _payloads(frames):
        try:
            node = json.loads(data)
        except ValueError:
            continue
        for p in parts:
            if isinstance(node, list):
                try:
                    node = node[int(p)]
                except (ValueError, IndexError):
                    node = None
            elif isinstance(node, dict):
                node = node.get(p)
            else:
                node = None
            if node is None:
                break
        if isinstance(node, str):
            out.append(node)
        elif isinstance(node, (int, float)):
            out.append(str(node))
    return "".join(out)


def describe(frames: list[Frame]) -> dict:
    """Facts about a stream that a report wants in one line.

    A stream consisting only of keep-alives is a real case -- it is
    what a server does for the thirty seconds before it decides it
    has nothing to say -- so every field here has to survive an empty
    event list rather than assuming there was a first frame.
    """
    events = [f for f in frames if f.kind != "comment"]
    comments = [f for f in frames if f.kind == "comment"]
    gaps = [b.t - a.t for a, b in zip(events, events[1:])]
    return {
        "frames": len(events),
        "keepalives": len(comments),
        "first_frame_s": round(events[0].t, 4) if events else None,
        "last_frame_s": round(events[-1].t, 4) if events else None,
        "max_gap_s": round(max(gaps), 4) if gaps else None,
        "keepalive_only": bool(comments) and not events,
        "done_sentinel": any(
            f.data.strip() == DONE_SENTINEL for f in events),
        "event_names": sorted({f.event for f in events if f.event}),
        "truncated": any(f.note == "eof" for f in events),
    }
