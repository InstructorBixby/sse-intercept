"""One place for mitmproxy version differences.

The stream hook -- assigning a callable to `flow.response.stream` in
`responseheaders` -- has been stable, which is the only thing this
tool genuinely depends on. Everything around it has moved once, and
putting the shims here keeps the addon readable and makes the support
range explicit rather than scattered across three modules.
"""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version


def mitmproxy_version() -> tuple[int, ...]:
    try:
        raw = version("mitmproxy")
    except PackageNotFoundError:        # pragma: no cover
        return (0,)
    parts = []
    for piece in raw.split("."):
        digits = "".join(c for c in piece if c.isdigit())
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts) or (0,)


def header_items(headers):
    """Headers as a list of pairs, duplicates preserved."""
    try:
        return list(headers.items(multi=True))
    except TypeError:                   # pragma: no cover
        return list(headers.items())


def make_options(listen_host, listen_port, confdir):
    from mitmproxy.options import Options

    opts = Options(listen_host=listen_host, listen_port=listen_port)
    # confdir stopped being an Options constructor keyword and is set
    # after construction instead. Setting it either way is harmless;
    # passing it to a constructor that does not take it is not.
    opts.update(confdir=confdir)
    return opts
