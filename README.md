# sse-intercept

An intercepting proxy for **streaming** HTTP responses:
`text/event-stream`, NDJSON, and raw chunked bodies. Each frame as it
arrives, with timing, changeable while the client is still reading.

## why I did not just use Burp

Burp buffers a streaming response. It appears in the history as one
body once the stream closes, which loses frame boundaries, loses the
timing between frames, and makes the one interesting intervention --
changing a frame mid-stream -- impossible, because by the time a
buffering proxy offers an edit the client has already consumed
everything.

`docs/why-not-burp.md` has the long version. Short version: Burp
models a response as a value, and a stream is not one. Everything
else still belongs in Burp.

## how I run it

    uv pip install -e ".[dev]" -c constraints-dev.txt

    # observe
    sseint proxy --allow-host api.example.test --record run.jsonl

    # intervene
    sseint proxy --allow-host @scope.txt --rules stall.yaml \
        --record run.jsonl

    # read it back
    sseint show run.jsonl --timing --histogram
    sseint show run.jsonl --reassemble json:choices.0.delta.content
    sseint show run.jsonl --resume
    sseint show run.jsonl --csv > frames.csv
    sseint view run.jsonl

    # the cheapest useful test: is the stream the same message?
    sseint compare run.jsonl --streamed 1 --whole 2

    # make a client bug reproducible without the server
    sseint replay run.jsonl --exchange 3 --speed 4

    # into whatever reads HAR
    sseint export run.jsonl --out run.har

Nothing is proxied until a host is named: an empty scope refuses every
request. The CA is mitmproxy's, at
`~/.mitmproxy/mitmproxy-ca-cert.pem`; import it into the client under
test and nowhere else. Credential headers are redacted from session
files unless you ask for them not to be, and a file written that way
says so in its own meta record.

## rules

```yaml
allow_hosts: [api.example.test]
rules:
  - id: stall-frame-5
    match: {path: /v1/stream, seq: 5}
    action: {delay: {s: 25}}
  - id: eat-the-sentinel
    match: {data_contains: "[DONE]"}
    action: drop
```

`drop`, `delay`, `rewrite`, `set_field`, `inject`, `pause`, `cut`.
Matched on host, path, frame number, kind, event name, or data.
`docs/rules.md`, and `docs/recipes.md` for the ones that have found
something.

## what it decodes

| content type | decoder |
|---|---|
| `text/event-stream` | SSE framing: all three separators, multi-line `data:`, comments, `event:` / `id:` / `retry:`, the `[DONE]` convention |
| `application/x-ndjson`, `application/jsonl`, `application/json-seq` | one JSON value per line |
| anything, with `--decoder chunked` | one frame per HTTP chunk |

Out-of-tree decoders load from an entry point: `docs/plugins.md`.

## limitations

Stated here rather than discovered later.

- **A `delay` or `pause` blocks mitmproxy's event loop** for its
  duration, so other flows on the same proxy stall while a frame is
  held. Not fixable without writing a second proxy. Aim a timing run
  at one host; the scope guard already pushes you that way.
- **Rules cost latency.** With an armed engine the relay decodes
  before forwarding. Every frame reports `+Nms by proxy` and the
  session records it, but do not compare timings across a run with
  rules and a run without.
- **No request-direction features.** mitmproxy already does that well;
  load the addon into mitmproxy yourself if you want both.
- **`compare` needs the non-streamed request issued by hand.** The
  tool does not make requests of its own, deliberately.
- **There is no `last` frame matcher** and there cannot be: nothing
  identifies the final frame until the stream has ended.
- **Only SSE, NDJSON and chunked.** Not WebSocket, not gRPC, and not
  Brotli or zstd content encoding -- those produce an encoding note
  rather than pretending the bytes are text. A private framing can
  live out of tree: `docs/plugins.md`.

## what I tried first

For the record, so I stop relitigating it at 2am.

| tool | why it did not do the job |
|---|---|
| **Burp Suite** | Buffers `text/event-stream`: one body after the stream closes, no frame boundaries, no timing, no mid-stream edit. Still where the rest of the application goes; this is aimed at one host alongside it. |
| **mitmproxy** | Does the hard parts -- CONNECT, CA, h2 -- and exposes the per-chunk hook this is built on, which is why the core ended up an addon. What it does not have is SSE framing, frame-level rules, reassembly, a frame timeline or replay. For watching bytes I still use it directly. |
| **browser devtools** | Show SSE frames and timing well, for a browser, read-only. No interception, no scripted stall, and nothing for the non-browser clients, which is most of what I test. |
| **`curl -N`** | Answers "does it stream" in one line and nothing past that. Still the first thing I reach for. |
| **Wireshark** | Everything, at the wrong layer, and TLS makes it a key-logging exercise before I see a frame. |

## docs

| file | what |
|---|---|
| `docs/why-not-burp.md` | the model problem, at length |
| `docs/running.md` | invocation, the CA, HTTP/2, the cost of a delay |
| `docs/decoders.md` | the decoder contract and the buffer caps |
| `docs/rules.md` | matching, actions, cost |
| `docs/recipes.md` | the tests that have found something |
| `docs/session-format.md` | the record format, redaction, rotation |
| `docs/export.md` | HAR, and what it cannot carry |
| `docs/unicode.md` | invisible codepoints in a stream |
| `docs/plugins.md` | writing a decoder that lives elsewhere |
| `docs/stability.md` | what the version number promises my own scripts |
| `docs/adding.md` | the bar a new decoder or action has to clear |
| `docs/careful.md` | where this can hurt me |
| `docs/builds.md` | telling two wheels apart |
| `docs/faq.md` | the things I keep having to look up again |
| `NOTES.md` | why it is shaped like this, and what I would change |

## layout

| path | what |
|---|---|
| `sseint/addon.py` | the mitmproxy addon; the streaming hook |
| `sseint/relay.py` | fast path and intercepting path, `feed(chunk) -> bytes` |
| `sseint/rules.py` | matching, and the op types |
| `sseint/apply.py` | ops to a plan |
| `sseint/decoders/` | stream decoders |
| `sseint/session.py` | record, rotate and read a session |
| `sseint/replay.py` | serve a recorded stream back |
| `sseint/resume.py` | did the reconnect actually resume |
| `sseint/viewmodel.py` | what the TUI shows; `view.py` only draws it |
| `sseint/compat.py` | mitmproxy version differences, in one place |
| `samples/` | a local server that misbehaves the way real ones do |
