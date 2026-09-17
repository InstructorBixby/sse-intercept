# Design notes

## why this exists

Every intercepting proxy I own treats a response as a value. It has a
status, headers and a body, and the body is complete by the time you
see it. That model is correct for almost all HTTP and wrong for
anything that streams, because for a stream the interesting facts are:

- where the frame boundaries are,
- how far apart in time they are,
- and whether the client behaves differently if one of them changes,
  arrives late, or never arrives.

None of those survive buffering. The first two are destroyed by it and
the third is not even expressible.

## the requirements

1. Never buffer a streaming body on the observation path.
2. Frame-level view with relative timing.
3. Frame-level actions, decided while the stream is open.
4. Reassembly, so a streamed response can be compared with the
   non-streamed response to the same request.
5. Record and replay, so a client-side bug is reproducible without the
   server.

All five are done. (4) has been the most productive per hour spent and
was the cheapest to build, which is the usual relationship.

## scope guard, first

A proxy that defaults to open is how you end up relaying traffic that
is not yours. Default deny, explicit host allowlist, no exceptions. It
is the only behaviour in here with a test that exists purely to stop
it regressing.

## the TLS stack had to go

The hand-rolled CONNECT and leaf-signing path did its job: it made the
interception path legible while the streaming parts were being worked
out. Then HTTP/2 came due, and a client that offers `h2` in ALPN and
gets HTTP/1.1 is being tested on a protocol it would not have used --
different response framing, different flow control, and therefore
different inter-frame gaps. Measuring token timing over a protocol the
client downgraded to at my insistence is measuring my own proxy.

mitmproxy already does CONNECT, its own CA, h2, and a per-chunk hook
on the response body, which is the one thing most proxies will not
give you and the only thing this tool needs from a proxy. The decoders
and the rule engine never touched a socket, so swapping the core was a
replacement of one module rather than a rewrite. That seam paid for
itself twice: once here, and again when `Relay.feed` became a pure
bytes-to-bytes function and the whole intercepting path became
testable without a port.

## what I would do differently

**Separate the ops from the plan sooner.** `apply.py` exists because
the relay had grown four flags that interacted, and the interactions
(inject-before plus drop, two delays, cut with a queue behind it) were
each discovered by getting them wrong first. A pure
`(frame, ops) -> plan` function should have been the first thing
written after the decoder, not the fifth.

**Not build a TLS stack at all.** It was interesting and it was six
weeks of the wrong work. The counter-argument is that writing it is
what made the h2 problem legible rather than theoretical, and I do not
fully dismiss that. But the honest version is that mitmproxy's
streaming hook was always the whole dependency, and I could have found
that out in an afternoon by reading its addon docs.

**Timing honesty earlier.** `added_ms` was retrofitted after I quoted
a gap in a report that included a 2.5 second delay the proxy had
introduced. Nobody noticed, which is worse. An instrument reports its
own contribution from the first version.

## what is still wrong

- A `delay` or `pause` blocks mitmproxy's event loop, so other flows
  stall while a frame is held. Not fixable without writing a second
  proxy; documented, and the scope guard already pushes a run toward
  one host.
- No request-direction features. Deliberate -- mitmproxy does that
  well -- but it means two tools for one engagement.
- `compare` needs two exchanges recorded by hand. It should be able to
  issue the non-streamed request itself, and the only reason it does
  not is that then the tool makes requests, which is a different
  safety conversation.
