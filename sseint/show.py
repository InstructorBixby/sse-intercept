"""Rendering a session as text."""
from __future__ import annotations

from sseint import visible
from sseint.reassemble import describe, reassemble
from sseint.resume import analyse as analyse_resume
from sseint.timing import analyse, histogram

MARKS = {"comment": ":", "event": "#", "line": ".", "chunk": "~"}


def render(meta, exchanges, *, only=None, reassemble_mode=None,
           timing=False, hist=False, resume=False, show_invisible=False,
           stall_s=1.0, width=100) -> str:
    out = [f"# format={meta.get('format')} "
           f"tool={meta.get('tool_version')} "
           f"redacted={meta.get('redacted', 'unknown')}"]
    if resume:
        return "\n".join(out + _resume(exchanges)) + "\n"
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
        hidden = _invisible_summary(ex)
        if hidden:
            out.append(f"      ! {hidden}")
        if timing:
            st = analyse(ex.frames, stall_s=stall_s, added=ex.added_ms)
            out += [f"      {line}" for line in st.lines()]
        if hist:
            out += [f"      {line}" for line in histogram(ex.frames)]
        if reassemble_mode:
            text = reassemble(ex.frames, reassemble_mode)
            out.append(visible.mark(text) if show_invisible else text)
            continue
        if timing or hist:
            continue
        for f in ex.frames:
            mark = MARKS.get(f.kind, "?")
            note = f"   [{f.note}]" if f.note else ""
            body = f.summary(width)
            if show_invisible:
                body = visible.mark(body)
            out.append(f"  {mark}{f.seq:<4} +{f.t:7.3f}s  "
                       f"{body}{note}")
    return "\n".join(out) + "\n"


def _invisible_summary(ex) -> str | None:
    """Say it even when --visible was not asked for.

    A frame that contains something invisible is worth flagging
    unprompted: the reason to look is that you cannot see it, so
    waiting for the operator to think of the flag defeats the point.
    """
    seqs = [f.seq for f in ex.frames if not visible.clean(f.data)]
    if not seqs:
        return None
    head = ", ".join(str(s) for s in seqs[:6])
    more = f" (+{len(seqs) - 6} more)" if len(seqs) > 6 else ""
    return (f"invisible or formatting codepoints in frame(s) {head}"
            f"{more}; --visible to see them")


def _resume(exchanges) -> list[str]:
    events = analyse_resume(exchanges)
    if not events:
        return ["", "no reconnects on the same path in this session"]
    out = ["", "reconnects:"]
    for r in events:
        out.append(f"  [{r.after}] -> [{r.exchange}]  "
                   f"last id seen {r.last_id_seen or '-'}, "
                   f"sent {r.last_id_sent or '-'}, "
                   f"{r.overlap} char(s) repeated")
        out.append(f"      {r.verdict()}")
    return out
