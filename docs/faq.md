# FAQ

**Does it work with Burp upstream?**

Yes, and that is the usual arrangement: Burp for the application,
this pointed at the one host whose streams you care about. The scope
guard is default-deny partly for this reason -- chaining two proxies
should not quietly put the whole application through the one that
writes transcripts to disk.

**Why is there no `last` matcher for the final frame?**

Nothing identifies the final frame until the stream has ended, and by
then the frame has been forwarded. A rule engine that could match
"last" would have to buffer the whole response, which is the behaviour
this tool exists to avoid. Match on content, or on `seq_from`.

**The gaps look longer than when I watch the client directly.**

Check whether rules were armed. With an armed engine the relay must
decode a frame before deciding what to do with it, so the proxy is in
the path; every frame line reports `+Nms by proxy` and the session
records it. With no rules, the chunk is handed straight back and
nothing is added. Do not compare timings across that boundary.

**A `delay` rule made the whole proxy unresponsive.**

Expected, documented in `docs/running.md`, and not fixable without
writing a second proxy: the delay blocks inside mitmproxy's stream
hook, which runs on its event loop. Aim a timing run at one host.

**Can it modify the request?**

No, deliberately. mitmproxy already does that well and the plain
`request` hook is available if you load the addon into mitmproxy
yourself. This tool is about the response direction, where nothing
else helps.

**Why does the session file not contain the raw bytes of every
frame?**

It does when they are not valid UTF-8. Otherwise frames are stored
decoded, because that is what diffs, greps and reads well, and the
fields round-trip back to the wire exactly -- there is a test that
re-encoding a parsed frame reproduces it.

**`show` says frames contain invisible codepoints. Is that bad?**

It is a fact, not a verdict. `--visible` shows what they are. For an
opinion, allowlists and confusable detection, `glyphstop` is installed
and this hands off to it -- `docs/unicode.md`.

**Why is HTTP/2 worth caring about here?**

Because response framing, flow control, and therefore the inter-frame
gaps are different, so measuring token timing over a protocol the
client was forced to downgrade from measures the proxy. The old
hand-rolled TLS stack could not do h2, which is most of why it was
replaced.
