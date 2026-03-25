# Out-of-tree decoders

A decoder can ship in its own package and register itself:

```toml
[project.entry-points."sseint.decoders"]
vnd-example = "mypkg.decoder:ExampleDecoder"
```

It must satisfy the contract in `docs/decoders.md` -- `name`,
`content_types`, `feed(chunk) -> list[Frame]`, `close() -> list[Frame]`
-- and it must not buffer without limit.

## why this exists

Two products I have tested ship a private framing on a private content
type. One of the decoders is fifteen lines. Neither belongs in this
repo: the built-in decoders are deliberately few, each one justified
by a framing that exists widely, and a private format fails that test
while still being worth having locally.

## rules

- A built-in name always wins. A plugin claiming `sse` is refused and
  said so on stderr, because a silently shadowed decoder would make
  every frame in a session wrong in a way nobody would think to check.
- A plugin that fails to import is reported and skipped. The proxy
  still starts: losing a decoder is not a reason to lose the run.
- A plugin that does not implement `feed` and `close` is refused.
- `sseint --version` is not the place to look for what loaded.
  `--decoder` lists what is available, including plugins.

`sseint.*` names are reserved for this repo.
