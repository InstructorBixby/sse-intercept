# sse-intercept

An intercepting proxy for **streaming** HTTP responses:
`text/event-stream`, NDJSON, and raw chunked bodies. See each frame as
it arrives, with timing, and change it while the client is still
reading.

```
uv pip install -e .
sseint proxy --allow-host api.example.test --record run.jsonl
```

## why it exists

Every intercepting proxy I own models a response as a value: status,
headers, and a body that is complete by the time I see it. That is
correct for almost all HTTP and wrong for a stream, where the facts
worth having are where the frame boundaries are, how far apart in time
they are, and what the client does if one of them changes, arrives
late, or never arrives.

Buffering destroys the first two and makes the third inexpressible.
See [Why not Burp](why-not-burp.md).

## where to look first

- [Running it](running.md) -- invocation, the CA, HTTP/2, and the one
  honest limitation.
- [Recipes](recipes.md) -- the seven tests that have actually found
  something. The first one needs no rules at all.
- [Rules](rules.md) -- the interception rule file.
- [Stability](stability.md) -- what the version number promises my
  own scripts.

## scope guard

Nothing is proxied until a host is named. An empty scope refuses every
request, CONNECT included. This is not caution for its own sake: this
laptop has a system proxy set half the time, and everything else on it
would quietly route through an instrument that writes transcripts to
disk.

## reading these

mkdocs-material, because search over fourteen notes beats grep when I
cannot remember which one said it:

    uv pip install -e ".[docs]"
    mkdocs serve

They have to stay readable as plain files in the checkout as well,
which is why there is nothing in them that only renders in the theme.
If a page needs the theme to make sense, the page is wrong.
