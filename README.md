# sse-intercept

An intercepting proxy for streaming HTTP responses: `text/event-stream`
first, then anything else that arrives in pieces.

## why I did not just use Burp

Burp buffers a streaming response. It shows up in the history as one
body once the stream closes, which loses three things:

- **frame boundaries.** A token stream is a sequence of small frames.
  Concatenated, they look like a normal response, and every question
  about framing -- are `data:` fields split per token or per word, does
  the server send a final sentinel, is the `event:` name consistent --
  becomes unanswerable.
- **timing.** The gap between frames is a measurement, not noise. A
  first-frame latency of two seconds followed by 40ms gaps is a
  different system from an even 150ms, and both are invisible once the
  body is a single value.
- **the intercept point.** By the time a buffering proxy offers you an
  edit, the client has already consumed the stream. Dropping frame 3,
  delaying frame 7 past the client's read timeout, or injecting a frame
  with no `event:` name are not expressible at all.

So: only the streaming case, without buffering. Burp keeps everything
else.

## how I run it

    pip install -e ".[dev]"
    sseint --allow-host api.example.test --port 8080

Nothing is proxied until a host is named: an empty scope refuses every
request, including CONNECT. The CA is generated on first run into
`ca/`; import `ca/ca.crt` into the client under test and nowhere else.

## what it decodes

| content type | decoder |
|---|---|
| `text/event-stream` | SSE framing: `data:` `event:` `id:` `retry:`, comments, `[DONE]` |

More to come -- NDJSON and raw chunked are the next two.

## layout

| path | what |
|---|---|
| `sseint/proxy.py` | CONNECT, TLS, the unbuffered relay |
| `sseint/decoders/` | content-type-aware stream decoders |
| `sseint/frame.py` | the unit everything deals in |
| `sseint/scope.py` | host allowlist, default deny |
| `sseint/tap.py` | where decoded frames go |
| `NOTES.md` | why it is shaped like this |
