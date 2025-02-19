"""Host allowlist.

Default deny. The tool will not open an upstream connection to a host
that was not named. This is not about the tool being attacked, it is
about the machine running it having a system proxy set and quietly
relaying everything else on the box through an instrument that writes
transcripts to disk.
"""
from __future__ import annotations

import fnmatch


class Scope:

    def __init__(self, patterns=()):
        self.patterns = [p.strip().lower() for p in patterns if p.strip()]

    def allows(self, host: str | None) -> bool:
        if not self.patterns:
            return False
        host = (host or "").lower()
        return any(fnmatch.fnmatch(host, p) for p in self.patterns)

    def __bool__(self) -> bool:
        return bool(self.patterns)

    def describe(self) -> str:
        if not self.patterns:
            return "empty (everything is refused)"
        return ", ".join(self.patterns)
