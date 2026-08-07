"""mitmproxy addon.

mitmproxy will hand over the response body a chunk at a time if you
assign a callable to `flow.response.stream` in the `responseheaders`
hook. That callable is invoked with each chunk as it arrives and
whatever it returns is what the client receives; it is called once
more with an empty bytestring at end of stream. That hook is the only
thing this tool needs from a proxy and the thing most proxies will not
give you.

Everything else here is wiring: options, the scope guard, choosing a
decoder, and handing frames to the relay. Version differences live in
compat.py.
"""
from __future__ import annotations

from mitmproxy import ctx, http

from sseint.compat import header_items
from sseint.decoders import by_name, for_content_type
from sseint.encoding import Inflater
from sseint.relay import Relay
from sseint.rulefile import RuleFileError, load
from sseint.rules import Context
from sseint.scope import Scope
from sseint.session import SessionWriter
from sseint.tap import ConsoleTap, TeeTap

STREAMING_TYPES = ("text/event-stream", "application/x-ndjson",
                   "application/jsonl", "application/x-jsonlines",
                   "application/json-seq")


class StreamTap:

    def __init__(self):
        self.scope = Scope()
        self.engine = None
        self.console = ConsoleTap()
        self.tap = self.console
        self.writer = None
        self.force_decoder = None
        self.pause_budget_s = 30.0
        self.redact = True
        self.max_session_bytes = None

    def load(self, loader):
        loader.add_option("sseint_allow_hosts", str, "",
                          "Comma-separated host globs this proxy may "
                          "talk to. Empty refuses everything.")
        loader.add_option("sseint_rules", str, "",
                          "Path to a YAML rule file.")
        loader.add_option("sseint_record", str, "",
                          "Path to a session file to append to.")
        loader.add_option("sseint_redact", bool, True,
                          "Redact credential headers in the session "
                          "file. A file written without this says so "
                          "in its meta record.")
        loader.add_option("sseint_max_session_bytes", int, 0,
                          "Rotate the session file at this size. 0 "
                          "uses the default; a negative value never "
                          "rotates.")
        loader.add_option("sseint_decoder", str, "",
                          "Force a decoder by name.")
        loader.add_option("sseint_pause_budget", int, 30,
                          "Seconds a paused stream is held before the "
                          "proxy releases it itself.")
        loader.add_option("sseint_quiet", bool, False,
                          "Exchanges only, no per-frame lines.")

    def configure(self, updated):
        if "sseint_allow_hosts" in updated:
            self.scope = Scope(
                ctx.options.sseint_allow_hosts.split(","))
        if "sseint_rules" in updated and ctx.options.sseint_rules:
            try:
                hosts, self.engine = load(ctx.options.sseint_rules)
            except RuleFileError as exc:
                raise ValueError(f"rule file: {exc}") from exc
            self.scope = Scope(list(self.scope.patterns) + hosts)
        if "sseint_redact" in updated:
            self.redact = ctx.options.sseint_redact
        if "sseint_max_session_bytes" in updated:
            raw = ctx.options.sseint_max_session_bytes
            self.max_session_bytes = (None if raw < 0
                                      else (raw or None))
        if "sseint_record" in updated and ctx.options.sseint_record:
            kwargs = {"redact_headers": self.redact}
            if self.max_session_bytes:
                kwargs["max_bytes"] = self.max_session_bytes
            self.writer = SessionWriter(ctx.options.sseint_record,
                                        **kwargs)
        if "sseint_quiet" in updated:
            self.console.quiet = ctx.options.sseint_quiet
        if "sseint_decoder" in updated:
            self.force_decoder = ctx.options.sseint_decoder or None
        if "sseint_pause_budget" in updated:
            self.pause_budget_s = float(ctx.options.sseint_pause_budget)
        self.tap = (TeeTap(self.console, self.writer) if self.writer
                    else self.console)

    def done(self):
        if self.writer:
            self.writer.close()

    def requestheaders(self, flow: http.HTTPFlow):
        host = flow.request.pretty_host
        if not self.scope.allows(host):
            self.console.refused(host)
            flow.response = http.Response.make(
                403, f"sse-intercept: {host} is not in scope\n".encode(),
                {"content-type": "text/plain"})

    def responseheaders(self, flow: http.HTTPFlow):
        if flow.response is None:
            return
        ctype = flow.response.headers.get("content-type", "")
        base = ctype.split(";")[0].strip().lower()
        decoder = (by_name(self.force_decoder) if self.force_decoder
                   else for_content_type(ctype))
        if decoder is None and base not in STREAMING_TYPES:
            return

        ex = self.tap.exchange(
            host=flow.request.pretty_host,
            method=flow.request.method,
            path=flow.request.path,
            status=f"{flow.response.status_code} {flow.response.reason}",
            headers=header_items(flow.response.headers),
            decoder=decoder.name if decoder else None)
        if self.writer:
            self.writer.exchange(
                ex, request_headers=header_items(flow.request.headers))

        if self.engine and flow.response.headers.get("content-length"):
            del flow.response.headers["content-length"]

        relay = Relay(
            decoder,
            Inflater(flow.response.headers.get("content-encoding")),
            self.tap, ex, self.engine,
            Context(host=flow.request.pretty_host,
                    path=flow.request.path.split("?")[0]),
            pause_budget_s=self.pause_budget_s)
        flow.response.stream = _streamer(relay, self.tap, ex)


def _streamer(relay: Relay, tap, ex):
    """Adapt the relay to mitmproxy's chunk callback."""
    finished = False

    def streamer(chunk: bytes) -> bytes:
        nonlocal finished
        if finished:
            return b""
        if chunk:
            return relay.feed(chunk)
        finished = True
        out = relay.finish()
        tap.end(ex)
        return out

    return streamer


addons = [StreamTap()]
