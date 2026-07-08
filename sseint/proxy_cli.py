"""The proxy subcommand's body.

cli.py is argparse and dispatch. This was the last subcommand still
implemented inline, which also meant the scope-refusal path -- the one
piece of this tool that must never regress -- was only reachable by
starting a proxy.
"""
from __future__ import annotations

import asyncio
import sys

from sseint.compat import make_options
from sseint.rulefile import RuleFileError, load


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


def resolve_scope(args, err=sys.stderr):
    """Return the host list, or None if the run must not start."""
    try:
        hosts = expand_hosts(args.allow_host)
    except OSError as exc:
        print(f"sseint: {exc}", file=err)
        return None
    if args.rules:
        try:
            extra, _ = load(args.rules)
        except RuleFileError as exc:
            print(f"sseint: {args.rules}: {exc}", file=err)
            return None
        hosts += extra
    hosts = [h for h in hosts if h.strip()]
    if not hosts:
        print("sseint: refusing to start with an empty scope. Pass "
              "--allow-host or put allow_hosts in the rule file.",
              file=err)
        return None
    return hosts


def settings_for(args, hosts) -> dict:
    out = {
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
        out[key] = value
    return out


def run(args) -> int:
    hosts = resolve_scope(args)
    if hosts is None:
        return 2

    # Imported here so the session subcommands work on a machine
    # without mitmproxy installed.
    from mitmproxy.tools.dump import DumpMaster

    from sseint.addon import StreamTap

    master = DumpMaster(
        make_options(args.host, args.port, args.confdir),
        with_termlog=False, with_dumper=False)
    master.addons.add(StreamTap())
    master.options.update(**settings_for(args, hosts))

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
