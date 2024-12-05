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
the third is not even expressible: by the time a buffering proxy offers
you an edit, the client has already seen the whole thing.

## so the requirements are

1. Never buffer a streaming body. Forward each chunk the instant it
   arrives, and decode a copy.
2. Frame-level view with relative timing.
3. Frame-level actions: drop, rewrite, inject, delay, pause. Decided
   per frame, while the stream is open.
4. Reassembly, so a streamed response can be compared with the
   non-streamed response to the same request. Those two disagreeing is
   a finding on its own.
5. Record and replay, so a client-side bug is reproducible without the
   server.

## scope guard, first

A proxy that defaults to open is how you end up relaying traffic that
is not yours. This one will take an explicit host allowlist and refuse
everything else, before it grows any other feature.
