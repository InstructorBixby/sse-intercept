"""What `--version` prints.

The number alone was not enough the day I had three wheels on three
machines, all of them claiming 1.2.1, built out of a working tree I
had been editing in between -- and one of them was dropping frames.
A build from the tag job carries its commit; an install out of a
checkout says so instead of guessing.
"""
from __future__ import annotations

from sseint import __version__


def describe() -> str:
    try:
        from sseint._build import COMMIT
    except ImportError:
        return f"{__version__} (checkout)"
    return f"{__version__} ({COMMIT[:12]})"
