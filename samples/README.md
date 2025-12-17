# samples

`stream_server.py` is a local SSE server that can be told to
misbehave. Every quirk in it came off a real endpoint:

| quirk | the real-world case |
|---|---|
| `crlf` | CRLF between fields, LF for the separator, in one response |
| `no-final-blank` | the last frame has no trailing blank line, so a naive parser drops it |
| `split-separator` | the blank line arrives in two TCP segments |
| `keepalive` | `:` comment frames interleaved with tokens |
| `gzip` | gzipped `text/event-stream`, flushed per frame |
| `gzip-unlabelled` | gzipped body with the `Content-Encoding` header stripped by something upstream |
| `no-sentinel` | ends without `[DONE]` |
| `stall` | a six-second gap in the middle |
| `content-length` | a `Content-Length` on a streaming response |
| `huge-frame` | a 200kB single frame |

The test suite runs the decoder against every one of them. A decoder
change that breaks any real server's framing should fail the build
here rather than on an engagement.
