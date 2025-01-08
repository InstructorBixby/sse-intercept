"""Host allowlist.

Default deny. The tool will not open an upstream connection to a host
that was not named on the command line. This is not paranoia about the
tool being attacked, it is about the machine running it having a
system proxy set and quietly relaying everything else on the box
through an instrument that writes transcripts to disk.
"""
import fnmatch


class Scope:

    def __init__(self, patterns=()):
        self.patterns = [p.strip().lower() for p in patterns if p.strip()]

    def allows(self, host):
        if not self.patterns:
            return False
        host = (host or "").lower()
        return any(fnmatch.fnmatch(host, p) for p in self.patterns)

    def __bool__(self):
        return bool(self.patterns)

    def describe(self):
        if not self.patterns:
            return "empty (everything is refused)"
        return ", ".join(self.patterns)
