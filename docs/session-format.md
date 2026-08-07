# Session files

One JSON object per line, append-only, flushed after every record.

Append-only and flushed because of how these runs end: the proxy is
killed, or the client crashes, or the laptop sleeps. A session must be
readable afterwards, and `tail -f` on a run in progress has to work. A
truncated final line is ignored by the reader rather than treated as
corruption.

```
{"t":"meta","format":3,"tool":"sse-intercept","tool_version":"1.3.0",
 "clock":"monotonic","started_at":1.7e9,"redacted":true}
{"t":"exchange","ex":1,"host":"api.example.test","method":"POST",
 "path":"/v1/stream","status":"200 OK","decoder":"sse",
 "request_headers":[["accept","text/event-stream"],
                    ["authorization","Bearer <redacted:40>"]],
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
| `meta` | `format` | bumped when a reader would misinterpret an older file |
| `meta` | `clock` | which clock `at` is measured against |
| `meta` | `redacted` | whether credential headers were redacted |
| `meta` | `part` | which file of a rotated session this is |
| `exchange` | `ex` | exchange number, referenced by every other record |
| `frame` | `at` | seconds since the first body byte of that exchange |
| `frame` | `added_ms` | latency the proxy itself added to this frame |
| `frame` | `ops` | rule ids that fired on this frame |
| `frame` | `raw_b64` | present only when the bytes are not valid UTF-8 |
| `rotate` | `next` | filename that continues this session |

`at` is relative and measured on a monotonic clock, because that is
what replay needs and because a wall clock on a sleeping laptop
produces negative gaps. The wall time of the run is in `meta` once, for
correlating with somebody else's logs.

Frames are stored decoded. A frame that did not decode cleanly keeps
its bytes in `raw_b64` as well, so replay stays byte-exact and a report
can show what arrived rather than what was understood.

## redaction

Credential headers -- `authorization`, `cookie`, `set-cookie`,
`x-api-key` and friends -- are replaced with a scheme, a short prefix
and a length. The prefix is enough to tell two keys apart across
exchanges, which is occasionally the finding, and far too little to
use.

`--no-redact` turns it off and the file's own `meta` record says so,
with a `warning` key. A session file with credentials in it should
announce itself.

Frame *bodies* are not scanned. Something that works on a whole
transcript with a reversible mapping is a different tool.

## rotation

`--max-session-bytes`, default 256MB. At the limit the writer emits a
`rotate` record naming the next file -- `run.jsonl`, `run.jsonl.1`,
`run.jsonl.2` -- and continues there. `sseint show` and the rest
follow the chain, so a rotated session is still one session; pass
`follow=False` to `session.read` to look at one file.

This exists because a day pointed at a chatty client produced a file
no editor would open and that `read()` would have pulled entirely into
memory. A negative value never rotates, for when the whole run has to
be one file.
