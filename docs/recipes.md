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
arrived on the connection. Worth knowing before anybody asks whether
signing the response body would help.

## 5. Does a resume actually resume?

    rules:
      - id: cut-halfway
        match: {seq: 10}
        action: cut

Then:

    sseint show run.jsonl --resume

    reconnects:
      [1] -> [2]  last id seen 9, sent -, 34 char(s) repeated
          client reconnected without Last-Event-ID; the server has no
          way to resume and the first part is repeated

Four outcomes, and the report tells them apart: resumed correctly;
reconnected with no header; reconnected with the wrong id; reconnected
with the right id and the server restarted anyway. The last two look
identical in a transcript and have different owners.

A client that does not reconnect at all shows up as no reconnect
record, which is its own answer.

## 6. What does the timing actually look like?

    sseint show run.jsonl --timing --histogram

Report time to first frame separately from the gap distribution. They
have different causes and conflating them produces a recommendation
that does not help. Subtract `added by proxy` before quoting anything
from a run that had rules armed.

## 7. Make a client bug reproducible

    sseint replay run.jsonl --exchange 3

Point the client at the replay server. The bug now happens on demand
with no dependency on the real service, which is the difference
between a ticket that gets fixed and one closed as not-reproducible.
