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

## so the requirements are

1. Never buffer a streaming body on the observation path.
2. Frame-level view with relative timing.
3. Frame-level actions, decided while the stream is open.
4. Reassembly, so a streamed response can be compared with the
   non-streamed response to the same request.
5. Record and replay, so a client-side bug is reproducible without the
   server.

## scope guard, first

A proxy that defaults to open is how you end up relaying traffic that
is not yours. Default deny, explicit host allowlist, no exceptions.

## the TLS stack has to go

The hand-rolled CONNECT and leaf-signing path has done its job: it
made the interception path legible while the streaming parts were
being worked out, and it is small enough to read in one sitting.

It is now the only part of the tool that is both hard and not the
point, and three things have come due at once.

**HTTP/2.** A client that sends `h2` in its ALPN list and gets an
HTTP/1.1 answer from the proxy is a client being tested on a protocol
it would not have used. The response framing is different -- DATA
frames, not chunked encoding -- and so are flow control, the window
updates that gate when the server may send the next token, and
therefore the inter-frame gaps. Measuring token timing over a protocol
the client downgraded to at my insistence is measuring my own proxy.
Implementing h2 properly means HPACK, stream multiplexing, flow
control and priorities, which is a project.

**Everything else about a modern handshake.** ALPN negotiation, SNI
edge cases, session resumption, and clients that pin. All solved
elsewhere, none of it interesting here.

**Maintenance.** Each of those is a long tail of small breakages in
the part of the tool whose correctness I care about least.

So: keep the decoders, the rule engine, the plan builder, the session
format and the replay server -- which is all of the value and almost
all of the tests -- and reimplement the interception core as a
mitmproxy addon. mitmproxy already does CONNECT, its own CA, h2, and
gives a per-chunk hook on the response body, which is the one thing
most proxies will not give you and the only thing this tool needs
from a proxy.

The decoders and the rule engine never touched a socket, which is why
this is a replacement of one module rather than a rewrite. That seam
paid for itself.

## what is lost

- A single-file dependency-light mode. Worth it.
- Control over exactly when a byte is written. A delay implemented
  inside a stream hook blocks mitmproxy's event loop, and therefore
  every other flow. Documented rather than hidden, and the answer is
  to scope the run to the host under test, which the scope guard
  already forces.
