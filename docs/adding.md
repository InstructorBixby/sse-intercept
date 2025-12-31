# The bar for adding something

Written down because the version of me at 1am on an engagement will
add a decoder for one endpoint and leave it in here forever.

## a new decoder

1. It handles a framing I have seen more than once, and I can name
   where. "A server might do this" is not enough; the decoders are
   small because each one earned its place.
2. It obeys the contract in `docs/decoders.md`: never blocks, never
   assumes a read is a frame, never swallows bytes, flushes on
   `close`.
3It has a quirk in `samples/stream_server.py` reproducing the framing,
   and a test that drives the decoder against it.

One client's private framing does not clear (1). That is what an
out-of-tree decoder is for.

## a new rule action

1. It asks a question about the *client* that cannot be asked another
   way. `drop`, `delay` and `cut` each exist because a real client
   handled one of them badly.
2. It is expressible as a pure function from a frame and the op to a
   plan, in `apply.py`, with tests. Anything that needs to reach into
   the socket is not an action.
3. The rule-file spelling goes in `docs/rules.md` at the same time,
   because the file format is the part I will be reading in six
   months, not the code.

## tests

`pytest -q`. Everything with a decision in it is tested without a
socket: the decoders take bytes, the engine takes frames, `apply`
takes ops, the view model takes exchanges. The only tests that bind a
port are `tests/test_integration.py` and one in `test_replay.py`.

If a change cannot be tested that way, the change is probably in the
wrong module.

## style

`ruff check .` and nothing else. Line length 88. No type-checker in CI
on purpose: the annotations are documentation here and I would rather
they stay honest than stay complete.
