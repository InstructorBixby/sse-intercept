# Changelog

Keep a Changelog format, semver versions.

## [0.4.0]

### Added
- `sseint compare`: diff a reassembled stream against the
  non-streamed response to the same request. The usual cause of a
  difference is a control that runs on a complete response and
  cannot run on a stream.

### Changed
- **The interception core is now a mitmproxy addon.** The
  hand-rolled CONNECT and TLS path is gone. HTTP/2 works, the
  handshake is somebody else's problem, and the CA is mitmproxy's
  at `~/.mitmproxy/mitmproxy-ca-cert.pem`. The decoders, rule
  engine, plan builder, session format and replay server are
  unchanged -- they never touched a socket.
- `Relay.feed(chunk) -> bytes` instead of writing to a file object,
  which is what let the same relay sit behind a stream hook.

### Removed
- `--ca-dir` and the generated local CA. Use `--confdir`.

### Known
- A `delay` or `pause` blocks mitmproxy's event loop for the
  duration, so other flows on the same proxy stall. Aim a timing
  run at one host. See `docs/running.md`.

## [0.3.0]

### Added
- Session recording: append-only JSON lines, flushed per record, so
  a killed run still leaves a readable file.
- `sseint replay` serves a recorded exchange back to a client at the
  original gaps, at a multiple of them, or with no gaps at all.
  Pacing is against one start time, so a slow write does not
  accumulate drift.
- `sseint show` prints a session, with `--reassemble`.

### Changed
- Subcommands: `proxy`, `replay`, `show`. The flat flag namespace
  had started to need sentences explaining which flags applied when.

## [0.2.0]

### Added
- NDJSON decoder, and a chunked decoder selected explicitly with
  `--decoder chunked` for streams with no framing convention.
- Incremental content decoding, so a gzipped stream shows frames as
  they arrive instead of everything at once at the end. A
  header/body encoding disagreement is reported on the exchange.
- Reassembly: `data`, `lines` and `json:<dotted.path>` modes, plus a
  summary of a stream's shape (frame count, keep-alives, first and
  last frame, largest gap, whether the sentinel arrived).
- Interception rules: `drop`, `delay`, `rewrite`, `set_field`,
  `inject`, `pause`, `cut`, loaded from a YAML rule file, matched on
  host, path, frame number, kind, event name or data.
- `--pause-budget`: a paused stream is released by the proxy rather
  than left to hit the client's read timeout.

### Changed
- The relay keeps its unbuffered fast path when no rule can match
  the exchange, and reports its own added latency per frame when a
  rule is armed.
- `Content-Length` is removed from a streaming response head while
  rules are armed.

## [0.1.0]

### Added
- CONNECT proxy with TLS interception and a locally generated CA.
- Unbuffered relay: bytes reach the client before they are decoded.
- SSE decoder: all three frame separators, multi-line `data:`,
  comment keep-alives, `event:` / `id:` / `retry:`, the `[DONE]`
  sentinel, and a flush at EOF for servers that omit the final
  blank line.
- Per-frame console view with time since the previous frame.
- `--allow-host` scope guard. An empty scope refuses everything.
- `sseint` console script.
