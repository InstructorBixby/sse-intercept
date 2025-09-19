"""Statistics about a stream's shape.

Reading three hundred `+0.043s` lines and forming an impression is not
measurement. These are the numbers that have actually mattered in a
report:

- **time to first frame**, separately from everything else. It is the
  only number a user perceives directly and it is usually dominated by
  something other than the model.
- **the gap distribution**, median and p95 rather than a mean. Token
  streams are long-tailed and the mean describes none of them.
- **stalls**: gaps above a threshold, listed individually with the
  frame they precede, because one 9-second gap in the middle is a
  different problem from an evenly slow stream and the mean hides it.
- **keep-alive interval**, which tells you the server's idle timeout
  configuration without asking anybody.
- **added_ms**, the proxy's own contribution, so a number is never
  quoted that includes the instrument.
"""
from __future__ import annotations

from dataclasses import dataclass, field


def percentile(values, q: float) -> float | None:
    """Nearest-rank percentile. No numpy for five numbers."""
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    k = max(0, min(len(ordered) - 1,
                   int(round(q / 100.0 * (len(ordered) - 1)))))
    return ordered[k]


@dataclass
class Stall:
    before_seq: int
    gap_s: float
    added_ms: int = 0


@dataclass
class Stats:
    frames: int = 0
    keepalives: int = 0
    first_frame_s: float | None = None
    total_s: float | None = None
    gap_p50: float | None = None
    gap_p95: float | None = None
    gap_max: float | None = None
    keepalive_interval_s: float | None = None
    added_ms_total: int = 0
    stalls: list[Stall] = field(default_factory=list)

    def lines(self) -> list[str]:
        def s(v):
            return "-" if v is None else f"{v:.3f}s"
        out = [
            f"frames            {self.frames}",
            f"keep-alives       {self.keepalives}"
            + (f" every ~{self.keepalive_interval_s:.1f}s"
               if self.keepalive_interval_s else ""),
            f"first frame       {s(self.first_frame_s)}",
            f"total             {s(self.total_s)}",
            f"gap p50 / p95     {s(self.gap_p50)} / {s(self.gap_p95)}",
            f"gap max           {s(self.gap_max)}",
        ]
        if self.added_ms_total:
            out.append(f"added by proxy    {self.added_ms_total}ms "
                       f"(excluded from nothing -- subtract it "
                       f"yourself before quoting a gap)")
        for st in self.stalls:
            out.append(f"  stall {st.gap_s:.3f}s before frame "
                       f"{st.before_seq}"
                       + (f" ({st.added_ms}ms of it the proxy)"
                          if st.added_ms else ""))
        return out


def analyse(frames, stall_s: float = 1.0, added=None) -> Stats:
    """`added` maps frame seq -> added_ms, from a session file."""
    added = added or {}
    events = [f for f in frames if f.kind != "comment"]
    keeps = [f for f in frames if f.kind == "comment"]
    st = Stats(frames=len(events), keepalives=len(keeps))
    if not events:
        return st
    st.first_frame_s = round(events[0].t, 6)
    st.total_s = round(events[-1].t, 6)
    gaps = []
    for a, b in zip(events, events[1:]):
        gap = b.t - a.t
        gaps.append(gap)
        if gap >= stall_s:
            st.stalls.append(Stall(before_seq=b.seq,
                                   gap_s=round(gap, 6),
                                   added_ms=added.get(b.seq, 0)))
    if gaps:
        st.gap_p50 = round(percentile(gaps, 50), 6)
        st.gap_p95 = round(percentile(gaps, 95), 6)
        st.gap_max = round(max(gaps), 6)
    if len(keeps) >= 2:
        kgaps = [b.t - a.t for a, b in zip(keeps, keeps[1:])]
        st.keepalive_interval_s = round(sum(kgaps) / len(kgaps), 3)
    st.added_ms_total = sum(added.values())
    return st


def histogram(frames, buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0),
              width: int = 40) -> list[str]:
    events = [f for f in frames if f.kind != "comment"]
    gaps = [b.t - a.t for a, b in zip(events, events[1:])]
    if not gaps:
        return []
    edges = list(buckets) + [float("inf")]
    counts = [0] * len(edges)
    for g in gaps:
        for i, edge in enumerate(edges):
            if g < edge:
                counts[i] += 1
                break
    peak = max(counts) or 1
    out = []
    lo = 0.0
    for edge, count in zip(edges, counts):
        label = ("    >" + f"{lo:g}s" if edge == float("inf")
                 else f"{lo:g}-{edge:g}s")
        bar = "#" * int(round(count / peak * width))
        out.append(f"{label:>12}  {bar} {count}")
        lo = edge if edge != float("inf") else lo
    return out
