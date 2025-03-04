"""Command line."""
from __future__ import annotations

import argparse
import sys

from sseint import __version__, tls
from sseint.proxy import Server
from sseint.scope import Scope
from sseint.tap import ConsoleTap


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="sseint",
        description="Intercepting proxy for streaming HTTP responses.")
    ap.add_argument("--version", action="version", version=__version__)
    ap.add_argument("--host", default="127.0.0.1",
                    help="listen address (default: loopback only)")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--allow-host", action="append", default=[],
                    metavar="GLOB",
                    help="host this proxy may connect to; repeatable. "
                         "Nothing is proxied without at least one.")
    ap.add_argument("--ca-dir", default="ca",
                    help="where the local CA lives; created if absent")
    ap.add_argument("--quiet", action="store_true",
                    help="exchanges only, no per-frame lines")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    scope = Scope(args.allow_host)
    if not scope:
        print("sseint: refusing to start with an empty scope. "
              "Pass --allow-host.", file=sys.stderr)
        return 2
    certs = tls.CertStore(args.ca_dir)
    tap = ConsoleTap(quiet=args.quiet)
    srv = Server((args.host, args.port), scope, certs, tap)
    print(f"sseint listening on {args.host}:{args.port}, scope: "
          f"{scope.describe()}", file=sys.stderr)
    print(f"CA: {args.ca_dir}/ca.crt", file=sys.stderr)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("", file=sys.stderr)
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
