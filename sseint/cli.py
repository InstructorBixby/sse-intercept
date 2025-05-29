"""Command line."""
from __future__ import annotations

import argparse
import sys

from sseint import __version__, tls
from sseint.decoders import BY_NAME
from sseint.proxy import Server
from sseint.rulefile import RuleFileError, load
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
    ap.add_argument("--rules", metavar="FILE",
                    help="YAML rule file; its allow_hosts are added "
                         "to --allow-host")
    ap.add_argument("--ca-dir", default="ca")
    ap.add_argument("--decoder", choices=sorted(BY_NAME),
                    help="force a decoder instead of dispatching on "
                         "content-type")
    ap.add_argument("--pause-budget", type=float, default=30.0,
                    metavar="SECONDS",
                    help="longest a paused stream is held before the "
                         "proxy releases it by itself")
    ap.add_argument("--quiet", action="store_true")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    engine = None
    hosts = list(args.allow_host)
    if args.rules:
        try:
            extra, engine = load(args.rules)
        except RuleFileError as exc:
            print(f"sseint: {args.rules}: {exc}", file=sys.stderr)
            return 2
        hosts += extra
    scope = Scope(hosts)
    if not scope:
        print("sseint: refusing to start with an empty scope. Pass "
              "--allow-host or put allow_hosts in the rule file.",
              file=sys.stderr)
        return 2
    certs = tls.CertStore(args.ca_dir)
    tap = ConsoleTap(quiet=args.quiet)
    srv = Server((args.host, args.port), scope, certs, tap,
                 engine=engine, force_decoder=args.decoder,
                 pause_budget_s=args.pause_budget)
    print(f"sseint listening on {args.host}:{args.port}, scope: "
          f"{scope.describe()}", file=sys.stderr)
    if engine:
        print(f"{len(engine.rules)} rule(s): "
              f"{', '.join(r.id for r in engine.rules)}",
              file=sys.stderr)
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
