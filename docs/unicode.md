# Invisible codepoints in a stream

`sseint show --visible` renders every codepoint that is invisible, or
that renders as something other than itself, as a named marker:

    #12   +0.431s  data: your balance is <RLO>42<PDF> dollars
    #13   +0.470s  data: <TAG+0049><TAG+0067>...

A frame is flagged even when `--visible` was not asked for, because
the reason to look is that you cannot see it, and waiting for the
operator to remember a flag defeats the point.

## why it belongs in this tool at all

A streamed response is where this gets interesting rather than merely
present. Three cases have come up:

- **The marker arrives in its own frame.** A control that inspects the
  complete response can see a bidi override and a matching pop; a
  control that inspects a frame sees one of them. `sseint compare`
  against the non-streamed response is the direct test.
- **The payload is split across frames.** Half of a Tags-block
  sequence in frame 12 and half in frame 13 defeats a per-frame
  filter completely, and the reassembled message still carries the
  instruction. This is the streaming version of a payload split across
  turns.
- **The transcript is the finding.** A test whose evidence is a frame
  view full of nothing is not evidence. Markers make the session file
  quotable in a report.

Cross-references into my own taxonomy, for the classes this touches:
`PI-008` (instructions in the Unicode Tags block), `PI-009` (homoglyph
substitution), `IPI-008` (invisible markup in retrieved content).

## what this is not

Shallow on purpose. It is a lookup table plus a Unicode category
check: named format characters, the Tags block, variation selectors,
private use areas, unassigned codepoints. It does not do confusable
skeletons, mixed-script detection, normalisation differences, or
per-path allowlists, and it has no opinion about whether what it found
is a problem.

That is `glyphstop`'s job, it does all of the above properly, and if
it is installed this module hands off to it rather than keeping a
second, worse table:

    uv pip install -e ~/src/glyphstop
    sseint show run.jsonl --reassemble data --visible

Keeping two tables in two tools is how they end up disagreeing, and
the one that disagrees is always the one in front of the client.
