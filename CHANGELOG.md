# Changelog

Keep a Changelog format, semver versions.

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
