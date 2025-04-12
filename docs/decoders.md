# Decoders

A decoder is fed bytes off the wire and returns whole frames. The
contract is small on purpose:

```python
class Decoder:
    name: str
    content_types: tuple[str, ...]
    def feed(self, chunk: bytes) -> list[Frame]: ...
    def close(self) -> list[Frame]: ...
```

Rules every decoder obeys:

- **Never block.** `feed` returns what it can and keeps the rest.
- **A read is not a frame.** Partial input is buffered, never guessed
  at.
- **Never swallow bytes.** Anything unparseable comes back as a frame
  with a `note`, because a blank view is indistinguishable from a
  stalled server.
- **`close` flushes.** A stream that ends without a terminator still
  sent its last frame.

## sse -- `text/event-stream`

Frame separator is a blank line, where blank means CRLF CRLF, LF LF or
CR CR; servers mix them within one response. `data:` fields accumulate
joined by newline. One leading space after the colon is stripped, and
only one. A line beginning with `:` is a comment, usually a keep-alive,
and is *not* a frame boundary -- reported as its own frame so the
keep-alive interval is visible, which is often what you wanted to know.

`[DONE]` is not in the spec. It is a convention shared by several
streaming chat APIs: a last frame whose data is that literal string.
Recognised because its absence is a finding.

## ndjson -- `application/x-ndjson` and friends

One JSON value per line. A line that does not parse is held and retried
with the next one, because at least one server pretty-prints into a
stream and a newline-splitter corrupts it.

## chunked -- explicit only

One frame per HTTP chunk, for streams that carry no framing convention
at all. Not selected by content type, ever: `application/json` is
overwhelmingly not a stream, and guessing would put a frame view on
every ordinary response in the session. Pass `--decoder chunked`.

## content encoding

Handled before the decoder, incrementally. A gzipped stream fed to
`gzip.decompress` yields nothing until the stream closes, which empties
the frame view and falsifies every timing number in it.

Timing is recorded from the arrival of the *compressed* chunk, because
that is when the bytes existed. If the server does not flush per frame,
frames arrive in bursts, and that burstiness is a property of the
server worth seeing rather than smoothing away.

If the declared encoding and the body disagree -- usually because
something upstream stripped `Content-Encoding` and forwarded the
compressed body -- the exchange gets a note. That disagreement is a
finding about the path, not an inconvenience.
