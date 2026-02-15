# What the version number promises

Semver. Not because anybody is installing this, but because I am: two
scoring scripts, a replay harness, a `plays` filter and at least four
engagement runbooks all call `sseint` by name, and the ones in
runbooks I paste without re-reading. Writing the surface down is how
I stop a tidy-up on a Sunday from silently breaking a capture on a
Tuesday.

Fixed, and only changed with the ceremony below:

- the `sseint` command line: subcommands, flags, exit status;
- the rule file format;
- the session file format, which has its own `format` integer in the
  `meta` record;
- the HAR export's documented fields, including `_frames`;
- the decoder contract in `docs/decoders.md`, and the
  `sseint.decoders` entry point group;
- everything re-exported from `sseint.api`.

Not fixed, and may change in a patch release: everything else,
including module layout, which module a class lives in, the view
model, and the shape of console output. When a script of mine breaks
on an upgrade it is because it imported from `sseint.session` instead
of `sseint.api`, and the fix is in the script.

## deprecation

Nothing in the list above is removed without going through this:

1. **Announced** in `CHANGELOG.md` under the release that deprecates
   it, naming the replacement and the version it will be removed in.
2. **Still works**, for at least one full minor release, and never
   fewer than six months from that release's date.
3. **Warns once per run** on stderr when used, saying what to use
   instead. Once, not per occurrence: a warning printed three hundred
   times is a warning I stop seeing.
4. **Removed** only in a major release.

A renamed flag keeps the old spelling as a hidden alias for that
period, because the spelling I am going to type is the one in my own
notes, and the place I find out otherwise is halfway through a
capture I cannot restart. `sseint --help` shows the new name only;
the old one is in the changelog.

Two things are exempt, and both are stated here rather than discovered
later:

- **A security fix may remove or restrict behaviour immediately.** If
  a flag turns out to be a way past the scope guard, it goes, in a
  patch, and the changelog says why.
- **A session `format` bump is not a deprecation.** Old files are
  still read -- `sseint show` reads every format it has ever written,
  and will keep doing so -- but a *writer* may stop producing an old
  format without ceremony.

## exit status

| code | meaning |
|---|---|
| 0 | did what was asked |
| 1 | `compare` found a difference |
| 2 | bad usage, a bad rule file, or a missing exchange |

Nothing else is defined. In particular the proxy exits 0 on
interrupt, because being stopped is how a proxy run ends.
