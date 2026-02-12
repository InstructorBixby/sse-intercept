# Releasing

Releasing means a tag and a wheel in the job artefacts. There is no
index, no registry, and nothing to announce.

1. `CHANGELOG.md`: move the entries into a new version section.
2. Bump `__version__` in `sseint/__init__.py` and `version` in
   `pyproject.toml`. They have to agree -- the tag job refuses a tag
   whose version does not match the source, because the thing I will
   be holding later is a wheel on some other machine, and its
   metadata is the only way to tell what is in it.
3. `git tag vX.Y.Z` and push the tag.

The pipeline runs the full suite, builds the sdist and wheel, and
keeps them against the tag. For this machine I do not use them at
all: `uv pip install -e .` out of the checkout, same as always. The
wheel is for the laptop that has to sit next to a client's client,
where I do not want a checkout, a toolchain, or a half-committed
experiment of mine.

A tag whose suite fails produces no wheel. The tag stays -- rewriting
a tag I have already pushed is worse than a gap in the sequence -- and
the next patch version supersedes it.
