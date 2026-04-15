# Changelog

Keep a Changelog format, semver versions.

## [1.1.0]

### Added
- Out-of-tree decoders load from the `sseint.decoders` entry point
  group. A built-in name always wins and a shadowing plugin is
  reported rather than silently loaded.
- `sseint show --resume`: per reconnect, what `id:` the client last
  received, what it sent in `Last-Event-ID`, how much content was
  repeated, and which of the four usual outcomes it was.

## [1.0.1]

### Fixed
- The SSE decoder no longer buffers without limit when a response
  body contains no frame separator at all, which is what an error
  page served with a streaming content type looks like. At the cap
  the buffer is surrendered as one frame marked `overlong`.

## [1.0.0]

### Added
- HAR export, with every frame in a `_frames` extension field and
  a statement on the log that the body was reassembled.
- Credential headers are redacted in session files by default;
  `--no-redact` is recorded in the file's own meta record.
- `samples/stream_server.py`: a local SSE server with eleven
  switchable misbehaviours, each copied off a real endpoint, and an
  integration test that runs the decoder against all of them.
- `docs/why-not-burp.md`, `docs/recipes.md`, `docs/stability.md`,
  `docs/adding.md`, `docs/careful.md`.
- Pinned dev constraints, cached in CI. Coverage on the pipeline,
  and the docs built with `--strict` on every push so a broken
  link fails rather than rots.
- Full package metadata: classifiers, project URLs, a `docs` extra.
- A tag job that builds the sdist and wheel and refuses a tag whose
  version does not match the source. The wheel is what goes onto a
  machine that is not this one; it is not published anywhere.
- A deprecation policy with teeth: announced in the changelog,
  still working for a full minor release and never under six
  months, warning once per run, removed only in a major. A renamed
  flag keeps the old spelling as a hidden alias, because the
  spelling in my own runbooks is the one I will type next, and I
  find out mid-capture.

### Changed
- Session format 2: `meta` records whether headers were redacted.
- `cli.py` is argparse and dispatch only; every subcommand body is
  callable without it, which is how the tests call them.

### Note
- First version I am prepared to depend on rather than keep
  reading. The command line, rule file, session format and HAR
  fields are fixed now -- see `docs/stability.md`.

## [0.5.0]

### Added
- Timing statistics: time to first frame reported separately, gap
  p50/p95/max, individually listed stalls, keep-alive interval, and
  the latency the proxy itself added.
- `sseint show --timing` and `--histogram`.
- `sseint view`: a curses frame browser with filtering, a detail
  pane, a timing pane and the reassembled message. The decisions
  about what is on screen live in `viewmodel.py` and are tested;
  the curses layer only draws.
- `sseint.api`: the surface my other code is allowed to import,
  fully annotated, plus `py.typed`. My two scripts on top of this
  both reached into modules that move every release, and both
  broke on a refactor I thought was internal.
- `mypy` in CI.

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
