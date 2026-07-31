"""Refuse a tag whose version does not match the source.

A wheel whose metadata disagrees with its tag is a wheel I cannot
reason about six months later, holding it on some other machine and
trying to work out what is in it.
"""
from __future__ import annotations

import os
import pathlib
import re
import sys

tag = os.environ["CI_COMMIT_TAG"].lstrip("v")
src = pathlib.Path("sseint/__init__.py").read_text()
m = re.search(r'__version__ = "([^"]+)"', src)
if m is None:
    sys.exit("no __version__ in sseint/__init__.py")
if m.group(1) != tag:
    sys.exit(f"tag {tag} != __version__ {m.group(1)}")
