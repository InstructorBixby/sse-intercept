# Running it

The interception core is a mitmproxy addon. `sseint proxy` is a
wrapper that builds the options and runs `DumpMaster` in-process, so
the usual invocation is unchanged:

    sseint proxy --allow-host api.example.test --rules r.yaml \
        --record run.jsonl

Pass anything else through with `--set`:

    sseint proxy --allow-host api.example.test \
        --set stream_large_bodies=1m --set ssl_insecure=true

Or load the addon into mitmproxy directly, which is what to do if you
want the mitmproxy TUI alongside the frame view:

    mitmproxy -s $(python -c "import sseint.addon as a; print(a.__file__)") \
        --set sseint_allow_hosts=api.example.test \
        --set sseint_rules=r.yaml

## the CA

mitmproxy's, at `~/.mitmproxy/mitmproxy-ca-cert.pem`, generated on
first run. Import it into the client under test and nowhere else. The
hand-rolled CA this tool used to generate is gone, along with the
hand-rolled TLS stack -- see `NOTES.md`.

## scope

Unchanged and still default-deny. `--allow-host` is enforced in
`requestheaders`, before an upstream connection exists: an
out-of-scope request is answered with a 403 generated locally.

## HTTP/2

Now handled, which it previously was not, and that matters more than
it sounds. A client that offers `h2` in ALPN and gets HTTP/1.1 is
being tested on a protocol it would not have chosen. Response framing
differs -- DATA frames rather than chunked encoding -- and so do flow
control and the window updates that gate when the server may send the
next token, and therefore the inter-frame gaps.

The decoders are unaffected, because they consume a byte stream and
mitmproxy hands over the reassembled DATA payloads. What changes is
that the timing numbers are now the client's real numbers.

## the cost of a delay

A `delay` or `pause` action blocks inside the stream hook, which runs
on mitmproxy's event loop. While a frame is held, other flows on the
same proxy are not serviced. There is no way around this that does not
amount to writing a second proxy.

In practice this is fine, because the scope guard already forces a run
to be aimed at one host, and a timing test wants one flow anyway. But
do not run a delay rule on a proxy that a whole browser is pointed at
and then draw conclusions from the other tabs.
