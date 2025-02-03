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
PARTIAL = max(len(s) for s in SEPARATORS) - 1

# Not in the spec. It is a convention that several streaming chat APIs
# share: a final frame whose data is the literal string "[DONE]",
# carrying no payload, marking end of message. Worth recognising
# because its absence is a finding -- a client that keys completion off
# this sentinel and never receives it is a client that hangs.
DONE_SENTINEL = "[DONE]"


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


def first(fields, name):
    for k, v in fields:
        if k == name:
            return v
    return None


def event_of(fields):
    return first(fields, "event")


def id_of(fields):
    return first(fields, "id")


def retry_of(fields):
    """retry: is milliseconds, and a non-integer must be ignored."""
    raw = first(fields, "retry")
    if raw is None:
        return None
    try:
        return int(raw.strip())
    except ValueError:
        return None


def is_done(fields):
    return data_of(fields).strip() == DONE_SENTINEL
