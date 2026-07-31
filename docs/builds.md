# Which build is this

Nothing here is published, which does not mean I always know what I
am looking at. Three laptops, three wheels, all of them 1.2.1, built
on three different days out of a working tree I had been editing in
between, and one of them was dropping frames. Working out which one
took an afternoon I would like back.

So:

- The tag job writes `sseint/_build.py` with the commit before it
  builds, and `sseint --version` prints the short SHA when it is
  there.
- An install out of a checkout prints `(checkout)` rather than
  pretending to know. Whatever is in my working tree is not a build
  and must not claim to be one.
- The job prints a SHA-256 per file. The artefacts expire never, so
  the hash in the job log and the hash of the file on the laptop
  either match or the file came from somewhere else.
- `constraints-dev.txt` at that tag is the dependency set. That is
  the question I actually ask -- which mitmproxy is this built
  against -- and `git show vX.Y.Z:constraints-dev.txt` answers it
  with no further machinery.

## what this is not

Not reproducible builds. The wheel is pure Python and the inputs are
pinned, but I have never checked that two builds are byte-identical
and will not write that down until I have.

Not a signature, and it does not need to be. The chain is: that hash,
in that job log, on my own instance, on my own network. Anybody in a
position to edit that job log has a great deal more of mine than a
wheel.
