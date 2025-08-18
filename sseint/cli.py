"""Command line."""
from __future__ import annotations

import argparse
import sys

from sseint import __version__, session, tls
from sseint.compare import compare
from sseint.decoders import BY_NAME
from sseint.proxy import Server
from sseint.reassemble import describe, reassemble
from sseint.replay import ReplayServer
from sseint.rulefile import RuleFileError, load
from sseint.scope import Scope
from sseint.session import SessionWriter
from sseint.tap import ConsoleTap, TeeTap


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
                        "Nothing is proxied without at least one.")
    p.add_argument("--rules", metavar="FILE")
    p.add_argument("--record", metavar="FILE")
    p.add_argument("--ca-dir", default="ca")
    p.add_argument("--decoder", choices=sorted(BY_NAME))
    p.add_argument("--pause-budget", type=float, default=30.0,
                   metavar="SECONDS")
    p.add_argument("--quiet", action="store_true")

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

    c = sub.add_parser(
        "compare",
        help="diff a reassembled stream against a non-streamed "
             "response to the same request")
    c.add_argument("session")
    c.add_argument("--streamed", type=int, required=True,
                   metavar="N", help="exchange number of the stream")
    c.add_argument("--whole", type=int, required=True, metavar="N",
                   help="exchange number of the non-streamed response")
    c.add_argument("--reassemble", default="data", metavar="MODE")
    return ap


def cmd_proxy(args) -> int:
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
    console = ConsoleTap(quiet=args.quiet)
    writer = SessionWriter(args.record) if args.record else None
    tap = TeeTap(console, writer) if writer else console
    srv = Server((args.host, args.port), scope,
                 tls.CertStore(args.ca_dir), tap, engine=engine,
                 force_decoder=args.decoder,
                 pause_budget_s=args.pause_budget)
    print(f"sseint listening on {args.host}:{args.port}, scope: "
          f"{scope.describe()}", file=sys.stderr)
    if engine:
        print(f"{len(engine.rules)} rule(s): "
              f"{', '.join(r.id for r in engine.rules)}",
              file=sys.stderr)
    if writer:
        print(f"recording to {writer.path}", file=sys.stderr)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("", file=sys.stderr)
    finally:
        srv.server_close()
        if writer:
            writer.close()
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
    print(f"# {args.session}  format={meta.get('format')} "
          f"tool={meta.get('tool_version')}")
    for ex in exchanges:
        if args.exchange and ex.n != args.exchange:
            continue
        print(f"\n[{ex.n}] {ex.method} {ex.host}{ex.path} -> "
              f"{ex.status}  decoder={ex.decoder or '-'}")
        shape = describe(ex.frames)
        print(f"      {shape['frames']} frame(s), "
              f"{shape['keepalives']} keep-alive(s), "
              f"first +{shape['first_frame_s']}s, "
              f"max gap {shape['max_gap_s']}s, "
              f"sentinel={shape['done_sentinel']}")
        for note in ex.notes:
            print(f"      ! {note}")
        if args.reassemble:
            print(reassemble(ex.frames, args.reassemble))
            continue
        for f in ex.frames:
            mark = {"comment": ":", "event": "#"}.get(f.kind, "~")
            note = f"   [{f.note}]" if f.note else ""
            print(f"  {mark}{f.seq:<4} +{f.t:7.3f}s  "
                  f"{f.summary(100)}{note}")
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


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return {"proxy": cmd_proxy, "replay": cmd_replay,
            "show": cmd_show, "compare": cmd_compare}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
