# Session files

One JSON object per line, append-only, flushed after every record.

Append-only and flushed because of how these runs end: the proxy is
killed, or the client crashes, or the laptop sleeps. A session must be
readable afterwards, and `tail -f` on a run in progress has to work.
A truncated final line is ignored by the reader rather than treated as
corruption.

```
{"t":"meta","format":1,"tool":"sse-intercept","tool_version":"0.3.0",
 "clock":"monotonic","started_at":1.7e9}
{"t":"exchange","ex":1,"host":"api.example.test","method":"POST",
 "path":"/v1/stream","status":"HTTP/1.1 200 OK","decoder":"sse",
 "request_headers":[["accept","text/event-stream"]],
 "response_headers":[["content-type","text/event-stream"]]}
{"t":"frame","ex":1,"seq":1,"at":0.412,"kind":"event",
 "fields":[["data","Hel"]],"comments":[]}
{"t":"frame","ex":1,"seq":2,"at":0.465,"kind":"event",
 "fields":[["data","lo"]],"comments":[]}
{"t":"end","ex":1,"frames":2,"at":0.465}
```

## fields

| record | key | meaning |
|---|---|---|
| all | `t` | record type |
| `meta` | `format` | this document's version; bumped on a breaking change |
| `meta` | `clock` | which clock `at` is measured against |
| `exchange` | `ex` | exchange number, referenced by every other record |
| `frame` | `at` | seconds since the first body byte of that exchange |
| `frame` | `added_ms` | latency the proxy itself added to this frame |
| `frame` | `ops` | rule ids that fired on this frame |
| `frame` | `raw_b64` | present only when the bytes are not valid UTF-8 |

`at` is relative and measured on a monotonic clock, because that is
what replay needs and because a wall clock on a sleeping laptop
produces negative gaps. The wall time of the run is in `meta` once,
for correlating with someone else's logs.

Frames are stored decoded. A frame that did not decode cleanly keeps
its bytes in `raw_b64` as well, so replay stays byte-exact and a
report can show what arrived rather than what was understood.
