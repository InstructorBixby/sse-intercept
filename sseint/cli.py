"""Command line: argparse and dispatch, nothing else.

Every subcommand body lives in a module that can be called without
argparse, because that is what the tests do.
"""
from __future__ import annotations

import argparse
import asyncio
import sys

from sseint import __version__, session
from sseint.compare import compare
from sseint.decoders import BY_NAME
from sseint.reassemble import reassemble
from sseint.replay import ReplayServer
from sseint.rulefile import RuleFileError, load
from sseint.show import render


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="sseint",
        description="Intercepting proxy for streaming HTTP responses.")
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("proxy", help="intercept live traffic")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8080)
    p.add_argument("--allow-host", action="append", default=[],
                   metavar="GLOB",
                   help="host this proxy may connect to; repeatable. "
                        "Nothing is proxied without at least one. "
                        "@FILE reads one glob per line.")
    p.add_argument("--rules", metavar="FILE")
    p.add_argument("--record", metavar="FILE")
    p.add_argument("--no-redact", action="store_true",
                   help="keep credential headers in the session file. "
                        "The file records that this was used.")
    p.add_argument("--decoder", choices=sorted(BY_NAME))
    p.add_argument("--pause-budget", type=int, default=30,
                   metavar="SECONDS")
    p.add_argument("--confdir", default="~/.mitmproxy")
    p.add_argument("--quiet", action="store_true")
    p.add_argument("--set", action="append", default=[],
                   metavar="OPT=VALUE",
                   help="passed through to mitmproxy")

    r = sub.add_parser("replay", help="serve a recorded stream")
    r.add_argument("session")
    r.add_argument("--exchange", type=int, default=1)
    r.add_argument("--host", default="127.0.0.1")
    r.add_argument("--port", type=int, default=8099)
    r.add_argument("--speed", default="1",
                   help="gap multiplier, or 'fast' for no gaps")

    s = sub.add_parser("show", help="print a recorded session")
    s.add_argument("session")
    s.add_argument("--exchange", type=int)
    s.add_argument("--reassemble", metavar="MODE",
                   help="data | lines | json:<dotted.path>")
    s.add_argument("--timing", action="store_true")
    s.add_argument("--histogram", action="store_true")
    s.add_argument("--resume", action="store_true",
                   help="report, per reconnect, whether the client "
                        "sent Last-Event-ID and whether the server "
                        "honoured it")
    s.add_argument("--visible", action="store_true",
                   help="render invisible codepoints as named markers")
    s.add_argument("--stall", type=float, default=1.0,
                   metavar="SECONDS")

    v = sub.add_parser("view", help="browse a session in the terminal")
    v.add_argument("session")

    c = sub.add_parser(
        "compare",
        help="diff a reassembled stream against a non-streamed "
             "response to the same request")
    c.add_argument("session")
    c.add_argument("--streamed", type=int, required=True, metavar="N")
    c.add_argument("--whole", type=int, required=True, metavar="N")
    c.add_argument("--reassemble", default="data", metavar="MODE")

    e = sub.add_parser("export", help="write a session out as HAR")
    e.add_argument("session")
    e.add_argument("--exchange", type=int)
    e.add_argument("--out", help="output path, or - for stdout")
    e.add_argument("--reassemble", default="data", metavar="MODE")
    return ap


def expand_hosts(values) -> list[str]:
    """Expand @FILE entries.

    A real engagement scope is a list somebody sent you. Retyping it
    as twenty flags is how a host gets missed in one direction or
    added in the other.
    """
    out = []
    for value in values:
        if value.startswith("@"):
            with open(value[1:], encoding="utf-8") as fh:
                for line in fh:
                    line = line.split("#", 1)[0].strip()
                    if line:
                        out.append(line)
        else:
            out.append(value)
    return out


def cmd_proxy(args) -> int:
    try:
        hosts = expand_hosts(args.allow_host)
    except OSError as exc:
        print(f"sseint: {exc}", file=sys.stderr)
        return 2
    if args.rules:
        try:
            extra, _ = load(args.rules)
        except RuleFileError as exc:
            print(f"sseint: {args.rules}: {exc}", file=sys.stderr)
            return 2
        hosts += extra
    if not [h for h in hosts if h.strip()]:
        print("sseint: refusing to start with an empty scope. Pass "
              "--allow-host or put allow_hosts in the rule file.",
              file=sys.stderr)
        return 2

    from mitmproxy.options import Options
    from mitmproxy.tools.dump import DumpMaster

    from sseint.addon import StreamTap

    opts = Options(listen_host=args.host, listen_port=args.port,
                   confdir=args.confdir)
    master = DumpMaster(opts, with_termlog=False, with_dumper=False)
    master.addons.add(StreamTap())
    settings = {
        "sseint_allow_hosts": ",".join(hosts),
        "sseint_rules": args.rules or "",
        "sseint_record": args.record or "",
        "sseint_redact": not args.no_redact,
        "sseint_decoder": args.decoder or "",
        "sseint_pause_budget": args.pause_budget,
        "sseint_quiet": args.quiet,
    }
    for raw in args.set:
        key, _, value = raw.partition("=")
        settings[key] = value
    master.options.update(**settings)
    print(f"sseint listening on {args.host}:{args.port}, "
          f"{len(hosts)} host(s) in scope: {', '.join(hosts)}",
          file=sys.stderr)
    if args.no_redact and args.record:
        print("warning: credential headers will be written to "
              f"{args.record}", file=sys.stderr)
    print(f"CA: {args.confdir}/mitmproxy-ca-cert.pem", file=sys.stderr)
    try:
        asyncio.run(master.run())
    except KeyboardInterrupt:
        print("", file=sys.stderr)
    return 0


def cmd_replay(args) -> int:
    _, exchanges = session.read(args.session)
    match = [e for e in exchanges if e.n == args.exchange]
    if not match:
        print(f"sseint: no exchange {args.exchange} in {args.session}",
              file=sys.stderr)
        return 2
    speed = 1e9 if args.speed == "fast" else float(args.speed)
    ex = match[0]
    srv = ReplayServer(ex, (args.host, args.port), speed=speed)
    print(f"replaying exchange {ex.n} ({len(ex.frames)} frames) on "
          f"http://{args.host}:{srv.port}{ex.path}", file=sys.stderr)
    try:
        srv.start()
        srv.thread.join()
    except KeyboardInterrupt:
        print("", file=sys.stderr)
    finally:
        srv.stop()
    return 0


def cmd_show(args) -> int:
    meta, exchanges = session.read(args.session)
    sys.stdout.write(render(
        meta, exchanges, only=args.exchange,
        reassemble_mode=args.reassemble, timing=args.timing,
        hist=args.histogram, resume=args.resume,
        show_invisible=args.visible, stall_s=args.stall))
    return 0


def cmd_view(args) -> int:
    from sseint.view import run
    _, exchanges = session.read(args.session)
    if not exchanges:
        print(f"sseint: {args.session} has no exchanges",
              file=sys.stderr)
        return 2
    run(exchanges)
    return 0


def cmd_compare(args) -> int:
    _, exchanges = session.read(args.session)
    by_n = {e.n: e for e in exchanges}
    for n in (args.streamed, args.whole):
        if n not in by_n:
            print(f"sseint: no exchange {n} in {args.session}",
                  file=sys.stderr)
            return 2
    streamed = reassemble(by_n[args.streamed].frames, args.reassemble)
    whole = reassemble(by_n[args.whole].frames, args.reassemble)
    result = compare(streamed, whole)
    print(result.report())
    return 0 if result.same else 1


def cmd_export(args) -> int:
    from sseint.export_cli import run
    return run(args)


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return {"proxy": cmd_proxy, "replay": cmd_replay,
            "show": cmd_show, "view": cmd_view,
            "compare": cmd_compare, "export": cmd_export}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
