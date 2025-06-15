# Rules

A rule is a match and one or more actions. Rules are evaluated in file
order against every decoded frame; all matching rules contribute
actions, except that a `drop` or a `cut` stops evaluation for that
frame.

```yaml
allow_hosts:
  - api.example.test

rules:
  - id: drop-the-third-token
    match: {path: /v1/stream, seq: 3}
    action: drop
```

## match

| key | means |
|---|---|
| `host` | glob against the request host |
| `path` | glob against the path, query string excluded |
| `seq` | frame number within this response, from 1 |
| `seq_from` / `seq_to` | inclusive range |
| `kind` | `event`, `comment`, `line`, `chunk` |
| `event` | exact `event:` field value |
| `data_contains` | substring of the joined `data` |
| `data_matches` | Python regex against the joined `data` |

An unknown key is an error. A typo would otherwise produce a rule that
never fires, and a rule that never fires is indistinguishable from a
client that handled the case properly.

There is no `last` matcher and there cannot be: nothing identifies the
final frame until the stream has ended, by which point the frame has
gone. Match on content or on `seq_from` instead.

## actions

| action | argument | effect |
|---|---|---|
| `drop` | -- | the client never sees this frame |
| `delay` | `{ms: N}` or `{s: N}` | hold this frame, then send it |
| `rewrite` | `{find, replace, regex}` | change every field value |
| `set_field` | `{name, value}` | set or add one field |
| `inject` | `"data: ..."` or `{text, where}` | emit an extra frame |
| `pause` | -- | hold the stream until released |
| `cut` | -- | close the response here |

`limit: N` caps how many times a rule fires per proxy run.

Delays add. Two rules each delaying 2s delay 4s.

`inject: {where: before}` emits even if the same frame is dropped,
which is the substitution case and the one worth having.

## recipes

**Does the client handle a gap?** Delay one frame past the read
timeout. Most streaming clients have a 10s idle timeout and most are
wrong about what to do when it fires.

```yaml
rules:
  - id: stall-frame-5
    match: {seq: 5}
    action: {delay: {s: 20}}
```

**Does anything downstream trust frame content?** Rewrite one frame
mid-stream so it contradicts the ones around it. If the rendered
output shows the rewritten content, nothing between the socket and the
screen distinguishes server content from content that merely arrived
on the connection.

**Does the client require the sentinel?** Cut before it.

```yaml
rules:
  - id: no-done
    match: {data_contains: "[DONE]"}
    action: drop
```

A client that hangs here is a client whose completion signal is a
string convention rather than end of body.

**Is an injected frame distinguishable from a real one?**

```yaml
rules:
  - id: inject-an-event
    match: {seq: 2}
    action: {inject: "event: token\ndata: from the proxy"}
```

## cost

When no rule can match an exchange, the relay forwards each chunk
before decoding a copy and adds no measurable latency. When a rule is
armed it must decode before forwarding, so the proxy is in the path:
every frame line then reports `+Nms by proxy` and the session file
records it per frame. Compare timings between runs with and without
rules, not across that boundary.

`Content-Length` is dropped from the response head while rules are
armed. A streaming response should not have one; at least one here
does, and a rewrite that changes the body length otherwise produces a
response the client truncates or waits forever for.
