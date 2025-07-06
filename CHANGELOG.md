# Changelog

Keep a Changelog format, semver versions.

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
