"""text/event-stream framing.

Splitting the byte stream on b"\n\n" is wrong twice over. A frame
separator is any of CRLF CRLF, LF LF or CR CR, and servers mix them --
one endpoint here sends CRLF between fields and LF for the blank line.
And a comment line (one starting with ":") is not a frame at all; it is
a keep-alive, and treating it as a frame boundary cuts real frames in
half.

So: find the earliest separator of any of the three shapes, parse the
block into fields, and tell the caller what kind of block it was.
"""
import re

SEPARATORS = (b"\r\n\r\n", b"\n\n", b"\r\r")
LINE_SPLIT = re.compile(r"\r\n|\n|\r")


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


def parse_block(block):
    """Parse one block into (fields, comments).

    fields is a list of (name, value) in wire order, because order is
    sometimes the finding.
    """
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
            # A line with no colon is a field name with an empty
            # value. The spec says so and at least one server relies
            # on it to send a bare "data" line.
            fields.append((line, ""))
            continue
        if value.startswith(" "):
            value = value[1:]
        fields.append((name, value))
    return fields, comments


def data_of(fields):
    """Join every data field with a newline, per spec."""
    return "\n".join(v for k, v in fields if k == "data")
