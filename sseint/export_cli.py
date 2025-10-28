"""The export subcommand's body, kept out of cli.py.

cli.py is argparse and dispatch. Anything with a decision in it goes
somewhere testable, which by now is most of the tool.
"""
from __future__ import annotations

import json
import pathlib
import sys

from sseint import session
from sseint.export import har


def run(args) -> int:
    meta, exchanges = session.read(args.session)
    if args.exchange:
        exchanges = [e for e in exchanges if e.n == args.exchange]
        if not exchanges:
            print(f"sseint: no exchange {args.exchange} in "
                  f"{args.session}", file=sys.stderr)
            return 2
    doc = har(meta, exchanges, mode=args.reassemble)
    text = json.dumps(doc, indent=1, ensure_ascii=False)
    if args.out in (None, "-"):
        sys.stdout.write(text + "\n")
    else:
        pathlib.Path(args.out).write_text(text + "\n",
                                          encoding="utf-8")
        print(f"{len(doc['log']['entries'])} entr(ies) -> {args.out}",
              file=sys.stderr)
    return 0
