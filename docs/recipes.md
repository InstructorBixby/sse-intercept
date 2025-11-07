# Recipes

Each of these has found a real defect more than once.

## 1. Does the streamed answer equal the non-streamed answer?

First thing to run against a new endpoint, because it needs no
intervention and no model behaviour.

    sseint proxy --allow-host api.example.test --record run.jsonl
    # send the same request twice, once streaming, once not
    sseint compare run.jsonl --streamed 1 --whole 2

A difference almost always means a control that runs on a complete
response and cannot run on a stream: a redaction pass, a safety check,
a markdown sanitiser, a link rewriter. The streamed path skips it.

## 2. Is the completion signal end-of-body or a string?

    rules:
      - id: eat-the-sentinel
        match: {data_contains: "[DONE]"}
        action: drop

A client that hangs has its completion logic keyed on a convention
rather than on the response ending.

## 3. Does the client survive a stall?

    rules:
      - id: stall
        match: {seq: 5}
        action: {delay: {s: 25}}

Most streaming clients have an idle timeout somewhere between 10 and
60 seconds and most are wrong about what to do when it fires: a
half-rendered message left on screen with no error, a retry that
duplicates the first half, or a spinner forever.

## 4. Does anything downstream distinguish server content from
connection content?

    rules:
      - id: forge
        match: {seq: 3}
        actions:
          - {inject: "event: token\ndata: ***", where: before}
          - drop

If the injected content renders identically, nothing between the
socket and the screen distinguishes what the server said from what
arrived on the connection. That is worth knowing before anybody asks
whether a signature on the response body would help.

## 5. Does a resume actually resume?

    rules:
      - id: cut-halfway
        match: {seq_from: 10, seq_to: 10}
        action: cut

Then look at the next request. A client that reconnects should send
`Last-Event-ID` with the last `id:` it saw. Many send no header and
start again, which duplicates content; a few send the wrong id. Run
`sseint show --timing` on both exchanges to see what the server did
with it.

## 6. What does the timing actually look like?

    sseint show run.jsonl --timing --histogram

Report time to first frame separately from the gap distribution. They
have different causes and conflating them produces a recommendation
that does not help.

## 7. Make a client bug reproducible

    sseint replay run.jsonl --exchange 3

Point the client at the replay server. The bug now happens on demand
with no dependency on the real service, which is the difference
between a ticket that gets fixed and a ticket that gets closed as
not-reproducible.
