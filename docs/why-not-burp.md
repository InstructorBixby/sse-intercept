# Why not Burp

Writing this down because I spent two days looking for the Burp
setting that would do it, and there is no setting. Burp is the right
tool for almost everything and the wrong tool for this -- not because
of a missing feature, because of a model.

## the model

In Burp a response is a value. It has a status line, headers and a
body, and by the time it is in the proxy history or the intercept tab,
the body is complete. Everything downstream is built on that: match
and replace, the comparer, Repeater, extensions.

For a `text/event-stream` the response is not a value, it is a
sequence of events with timing. Buffering it is not a display
limitation, it collapses the dimension the response exists in.

## what that costs, concretely

**Frame boundaries.** A token stream is a sequence of small frames.
Concatenated, they look like an ordinary response. Everything about
framing then becomes unanswerable:

- Is `data:` split per token, per word, per sentence? Changes what a
  client's incremental renderer has to handle.
- Is there a final sentinel, and is it `[DONE]`, an empty `data:`, or
  nothing at all? A client that keys completion off a string
  convention hangs when the convention changes.
- Is the `event:` name consistent across frames? Clients switch on it.
- Are there `id:` values, and are they monotonic? They are what a
  resume after a dropped connection is built on.
- What is the keep-alive interval? It tells you the server's idle
  timeout without having to ask anyone.

**Timing.** The gap between frames is a measurement. Two seconds to
first frame and then 40ms gaps is a different system from an even
150ms -- different bottleneck, different user experience, different
fix. Once the body is a single value both look identical, and the
thing a user actually perceives (time to first frame) is not recorded
anywhere.

**The intercept point.** This is the one that matters. A buffering
proxy can only offer an edit after the stream has closed, by which
time the client has consumed all of it. None of the following is
expressible:

- drop frame 3 and see whether the client assumes contiguous ids;
- delay frame 7 past the client's read timeout;
- rewrite frame 40 so it contradicts frame 39, and see whether
  anything between the socket and the screen notices;
- cut the response before the sentinel;
- inject a frame the server never sent, and see whether anything
  downstream can tell the difference.

Each of those is a question about the client, and a buffering proxy
cannot ask any of them.

## what Burp still does better

Everything else, and I am not reimplementing any of it: scope and
site map, Repeater, the scanner, session handling rules,
authentication, extensions, the request editor.

The workflow that actually happens: Burp upstream of this, or this
pointed at one host while Burp handles the rest of the application. The
scope guard here is default-deny precisely so that running two proxies
in a chain does not quietly put the whole application through the
instrument that writes transcripts to disk.

## and the honest limitation

A `delay` or `pause` here blocks the event loop for its duration, so
other flows stall while a frame is held. See `docs/running.md`. Burp
does not have that problem because Burp does not do this.
