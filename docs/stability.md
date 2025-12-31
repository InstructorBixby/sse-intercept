# What the version number promises

Semver, and the number is for my benefit: my runbooks call this by
name and I do not re-read them before pasting. So, fixed:

- the `sseint` command line: subcommands, flags, exit status;
- the rule file format;
- the session file format, which has its own `format` integer in the
  `meta` record;
- the HAR export's documented fields, including `_frames`;
- the decoder contract in `docs/decoders.md`.

Not fixed, and may change in a patch release: everything else,
including module layout, the `Frame` dataclass, the view model, and
the shape of console output.

## session files

The `format` integer is bumped when a reader would misinterpret an
older file. Adding a key is not a bump; changing what a key means is.
A reader must ignore keys it does not know, and `sseint show` will
read any format it has ever written.

## exit status

| code | meaning |
|---|---|
| 0 | did what was asked |
| 1 | `compare` found a difference |
| 2 | bad usage, a bad rule file, or a missing exchange |

Nothing else is defined. In particular the proxy exits 0 on
interrupt, because being stopped is how a proxy run ends.
