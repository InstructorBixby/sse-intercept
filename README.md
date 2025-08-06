# sse-intercept

An intercepting proxy for streaming HTTP responses: `text/event-stream`,
NDJSON, and raw chunked bodies.

## why I did not just use Burp

Burp buffers a streaming response. It appears in the history as one
body once the stream closes, which loses three things:

- **frame boundaries.** A token stream is a sequence of small frames.
  Concatenated they look like an ordinary response, and every question
  about framing -- is `data:` split per token or per word, is there a
  final sentinel, is the `event:` name consistent -- becomes
  unanswerable.
- **timing.** The gap between frames is a measurement. Two seconds to
  first frame then 40ms gaps is a different system from an even 150ms,
  and both look identical once the body is a single value.
- **the intercept point.** By the time a buffering proxy offers an
  edit, the client has consumed the stream. Dropping frame 3, delaying
  frame 7 past the client's read timeout, cutting before the sentinel,
  or injecting a frame the server never sent are not expressible.

So: the streaming case only, without buffering.

## how I run it

    pip install -e ".[dev]"

    # observe
    sseint proxy --allow-host api.example.test --record run.jsonl

    # intervene
    sseint proxy --rules drop-sentinel.yaml --record run.jsonl

    # read it back
    sseint show run.jsonl --reassemble json:choices.0.delta.content

    # make a client bug reproducible without the server
    sseint replay run.jsonl --exchange 3 --speed 4

Nothing is proxied until a host is named: an empty scope refuses every
request, CONNECT included. The CA is generated on first run into
`ca/`; import `ca/ca.crt` into the client under test and nowhere else.

## what it decodes

| content type | decoder |
|---|---|
| `text/event-stream` | SSE framing: `data:` `event:` `id:` `retry:`, comments, `[DONE]` |
| `application/x-ndjson`, `application/jsonl` | one JSON value per line |
| anything, with `--decoder chunked` | one frame per HTTP chunk |

## docs

| file | what |
|---|---|
| `docs/decoders.md` | the decoder contract and what each one assumes |
| `docs/rules.md` | matching, actions, and the recipes worth having |
| `docs/session-format.md` | the record format |
| `NOTES.md` | why it is shaped like this |

## layout

| path | what |
|---|---|
| `sseint/proxy.py` | CONNECT, TLS, sockets |
| `sseint/relay.py` | the streaming relay, fast path and intercepting path |
| `sseint/rules.py` | matching, and the op types |
| `sseint/apply.py` | ops to a plan the relay can execute |
| `sseint/decoders/` | content-type-aware stream decoders |
| `sseint/session.py` | record and read a session |
| `sseint/replay.py` | serve a recorded stream back |
| `sseint/scope.py` | host allowlist, default deny |
