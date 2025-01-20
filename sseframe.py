"""text/event-stream framing.

Splitting the byte stream on b"\n\n" is wrong twice over. A frame
separator is any of CRLF CRLF, LF LF or CR CR, and servers mix them --
one endpoint here sends CRLF between fields and LF for the blank line.
And a comment line (one starting with ":") is not a frame at all; it is
a keep-alive, and treating it as a frame boundary cuts real frames in
half.

The other thing a parser has to get right is that a read is not a
frame. Nothing guarantees a chunk ends on a boundary; in practice a
slow token stream delivers one frame per segment and then, once per
run, delivers a separator split down the middle -- CR LF CR in one
segment and LF in the next. Treating CR LF CR as "no separator yet" is
correct, but only if the buffer tail is kept rather than scanned and
discarded, which is what the first version did.
"""
import re

SEPARATORS = (b"\r\n\r\n", b"\n\n", b"\r\r")
LINE_SPLIT = re.compile(r"\r\n|\n|\r")
# Longest separator minus one byte: the most that can be a prefix of a
# separator we have not finished receiving.
PARTIAL = max(len(s) for s in SEPARATORS) - 1


def split_block(buf):
    """Return (block, rest) or (None, buf) if no complete block yet."""
    best = None
    for sep in SEPARATORS:
        i = buf.find(sep)
        if i != -1 and (best is None or i < best[0]):
            best = (i, len(sep))
    if best is None:
        return None, buf
    i, n = best
    return buf[:i], buf[i + n:]


def could_be_partial_separator(buf):
    """True if the buffer tail might be the start of a separator.

    Only used for diagnostics -- split_block already does the right
    thing by leaving the tail alone -- but it makes the "waiting on a
    boundary" state visible in the frame view, which is the difference
    between a stalled server and a stalled parser.
    """
    tail = buf[-PARTIAL:]
    return any(s.startswith(tail) for s in SEPARATORS if tail)


def parse_block(block):
    """Parse one block into (fields, comments)."""
    text = block.decode("utf-8", "replace")
    fields = []
    comments = []
    for line in LINE_SPLIT.split(text):
        if not line:
            continue
        if line.startswith(":"):
            comments.append(line[1:])
            continue
        name, sep, value = line.partition(":")
        if not sep:
            fields.append((line, ""))
            continue
        if value.startswith(" "):
            value = value[1:]
        fields.append((name, value))
    return fields, comments


def data_of(fields):
    """Join every data field with a newline, per spec."""
    return "\n".join(v for k, v in fields if k == "data")
