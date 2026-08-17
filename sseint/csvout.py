"""Frame timings as CSV.

A report wants a table and a spreadsheet wants a file. Writing this
out by hand from `--timing` output, twice, was enough.

One row per frame, with the gap already computed, because the gap is
what gets plotted and computing it in a spreadsheet is where the
off-by-one lives.
"""
from __future__ import annotations

import csv
import io

COLUMNS = ["exchange", "host", "path", "seq", "kind", "at_s", "gap_s",
           "bytes", "added_ms", "ops", "note"]


def rows(exchanges):
    for ex in exchanges:
        prev = None
        for f in ex.frames:
            gap = "" if prev is None else round(f.t - prev, 6)
            prev = f.t
            yield {
                "exchange": ex.n,
                "host": ex.host,
                "path": ex.path,
                "seq": f.seq,
                "kind": f.kind,
                "at_s": round(f.t, 6),
                "gap_s": gap,
                "bytes": len(f.raw) or len(f.data.encode("utf-8")),
                "added_ms": ex.added_ms.get(f.seq, 0),
                "ops": " ".join(ex.ops.get(f.seq, [])),
                "note": f.note or "",
            }


def write(exchanges, fh=None) -> str:
    out = fh or io.StringIO()
    writer = csv.DictWriter(out, fieldnames=COLUMNS,
                            lineterminator="\n")
    writer.writeheader()
    for row in rows(exchanges):
        writer.writerow(row)
    return out.getvalue() if fh is None else ""
