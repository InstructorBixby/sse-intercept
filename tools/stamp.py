"""Write the commit into the package, just before it is built.

Only the tag job runs this. An install out of a checkout has no
`_build.py` and says `(checkout)` rather than guessing, because the
guess is the part that cost me the afternoon.
"""
from __future__ import annotations

import os
import pathlib

sha = os.environ["CI_COMMIT_SHA"]
pathlib.Path("sseint/_build.py").write_text(
    "# Written by the tag job. Absent in a checkout install.\n"
    f'COMMIT = "{sha}"\n')
