"""Stream decoders, chosen by content type.

A decoder is fed bytes and returns whole frames. It must never block,
never assume a read lands on a frame boundary, never swallow bytes it
cannot parse, and never buffer without limit.

Out-of-tree decoders load from the `sseint.decoders` entry point
group. The reason is specific: a couple of products ship a private
framing on a private content type, the decoder for one of them is
fifteen lines, and neither belongs in this repo. A built-in name
always wins over a plugin with the same name, and the plugin is
reported rather than silently shadowed.
"""
from __future__ import annotations

import sys
from importlib.metadata import entry_points

from sseint.decoders.chunked import ChunkedDecoder
from sseint.decoders.ndjson import NDJSONDecoder
from sseint.decoders.sse import SSEDecoder

BUILTIN = [SSEDecoder, NDJSONDecoder, ChunkedDecoder]
GROUP = "sseint.decoders"


def _load_plugins(warn=True):
    found = []
    for ep in entry_points(group=GROUP):
        try:
            cls = ep.load()
        except Exception as exc:               # noqa: BLE001
            if warn:
                print(f"sseint: decoder plugin {ep.name!r} failed to "
                      f"load: {exc}", file=sys.stderr)
            continue
        if not hasattr(cls, "feed") or not hasattr(cls, "close"):
            if warn:
                print(f"sseint: decoder plugin {ep.name!r} does not "
                      f"implement feed/close, ignoring",
                      file=sys.stderr)
            continue
        found.append(cls)
    return found


def registry(warn=True):
    builtin_names = {cls.name for cls in BUILTIN}
    out = list(BUILTIN)
    for cls in _load_plugins(warn=warn):
        if getattr(cls, "name", None) in builtin_names:
            if warn:
                print(f"sseint: decoder plugin {cls.name!r} shadows a "
                      f"built-in and was not loaded", file=sys.stderr)
            continue
        out.append(cls)
    return out


REGISTRY = registry()
BY_NAME = {cls.name: cls for cls in REGISTRY}


def for_content_type(ctype: str | None):
    base = (ctype or "").split(";")[0].strip().lower()
    for cls in REGISTRY:
        if base in cls.content_types:
            return cls()
    return None


def by_name(name: str):
    cls = BY_NAME.get(name)
    return cls() if cls else None
