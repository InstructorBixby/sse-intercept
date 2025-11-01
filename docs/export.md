# Export

    sseint export run.jsonl --out run.har

HAR 1.2, because that is what the rest of the toolchain reads. HAR has
no concept of a stream, so the export is lossy in a specific, stated
way rather than quietly.

| HAR field | what sse-intercept puts there |
|---|---|
| `response.content.text` | the **reassembled** message |
| `timings.wait` | time to first frame |
| `timings.receive` | first frame to last frame |
| `entry._frames` | every frame: seq, relative time, fields, rules fired, proxy latency |
| `entry._notes` | the exchange's notes |
| `log._sseint` | a statement that the body was reassembled, and by which mode |

A leading underscore is HAR's own convention for a custom field, so a
reader that does not understand `_frames` ignores it instead of
rejecting the file.

`log._sseint.note` exists so that nobody quotes `content.text` in a
report as if it had arrived as one body. It did not. If the point being
made is about framing or timing, cite `_frames`, or better, attach the
session file -- it is the primary artefact and HAR is a convenience.

`httpVersion` is left empty rather than guessed. The proxy knows what
it negotiated upstream and that is not necessarily what the client
negotiated with the proxy, and putting one of the two in a field
labelled with neither is how a report ends up asserting something
false about h2.
