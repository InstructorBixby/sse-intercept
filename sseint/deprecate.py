"""One place for deprecation warnings.

Warn once per process, on stderr, naming the replacement and the
version the old spelling goes away in. Once rather than per
occurrence: a warning printed three hundred times is a warning nobody
reads, and this tool's output is already dense.

Using `warnings` instead was the obvious thing and the wrong one --
the audience is somebody watching a terminal, and `-W` filters mean a
warning that matters can be silenced by a setting nobody set
deliberately.
"""
from __future__ import annotations

import sys

_said: set[str] = set()


def warn(old: str, new: str, *, removed_in: str,
         err=None) -> None:
    if old in _said:
        return
    _said.add(old)
    print(f"sseint: {old} is deprecated, use {new}. It will be "
          f"removed in {removed_in}.", file=err or sys.stderr)


def reset() -> None:
    """For tests. A process only warns once, which tests must undo."""
    _said.clear()
