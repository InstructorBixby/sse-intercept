"""Rendering a session as text.

Pulled out of cli.py once it grew three modes: the printing is worth
testing and argparse plumbing is not.
"""
from __future__ import annotations

from sseint.reassemble import describe, reassemble
from sseint.timing import analyse, histogram

MARKS = {"comment": ":", "event": "#", "line": ".", "chunk": "~"}


def render(meta, exchanges, *, only=None, reassemble_mode=None,
           timing=False, hist=False, stall_s=1.0, width=100) -> str:
    out = [f"# format={meta.get('format')} "
           f"tool={meta.get('tool_version')}"]
    for ex in exchanges:
        if only and ex.n != only:
            continue
        out.append("")
        out.append(f"[{ex.n}] {ex.method} {ex.host}{ex.path} -> "
                   f"{ex.status}  decoder={ex.decoder or '-'}")
        shape = describe(ex.frames)
        out.append(f"      {shape['frames']} frame(s), "
                   f"{shape['keepalives']} keep-alive(s), "
                   f"sentinel={shape['done_sentinel']}, "
                   f"truncated={shape['truncated']}")
        for note in ex.notes:
            out.append(f"      ! {note}")
        if timing:
            st = analyse(ex.frames, stall_s=stall_s, added=ex.added_ms)
            out += [f"      {line}" for line in st.lines()]
        if hist:
            out += [f"      {line}" for line in histogram(ex.frames)]
        if reassemble_mode:
            out.append(reassemble(ex.frames, reassemble_mode))
            continue
        if timing or hist:
            continue
        for f in ex.frames:
            mark = MARKS.get(f.kind, "?")
            note = f"   [{f.note}]" if f.note else ""
            out.append(f"  {mark}{f.seq:<4} +{f.t:7.3f}s  "
                       f"{f.summary(width)}{note}")
    return "\n".join(out) + "\n"
