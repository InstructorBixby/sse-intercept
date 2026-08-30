"""The alias has to keep working, and has to say it is going away.

A flag rename is cheap for me and expensive for whoever has it in a
runbook, so the shim gets a test rather than a promise.
"""
from __future__ import annotations

from sseint import deprecate, session
from sseint.cli import main
from sseint.decoders.sse import SSEDecoder
from sseint.tap import Exchange


def write_session(path):
    w = session.SessionWriter(path)
    ex = Exchange(n=1, host="h", method="GET", path="/s",
                  status="200 OK",
                  headers=[("content-type", "text/event-stream")],
                  decoder="sse")
    w.exchange(ex)
    d = SSEDecoder()
    for f in d.feed("data: hel\u200blo\n\n".encode()) + d.close():
        ex.frames.append(f)
        w.frame(ex, f)
    w.end(ex)
    w.close()


def test_new_flag_renders_markers(tmp_path, capsys):
    s = tmp_path / "s.jsonl"
    write_session(s)
    assert main(["show", str(s), "--show-invisible"]) == 0
    assert "<ZWSP>" in capsys.readouterr().out


def test_old_flag_still_works(tmp_path, capsys):
    deprecate.reset()
    s = tmp_path / "s.jsonl"
    write_session(s)
    assert main(["show", str(s), "--visible"]) == 0
    out = capsys.readouterr()
    assert "<ZWSP>" in out.out


def test_old_flag_warns_and_names_the_replacement(tmp_path, capsys):
    deprecate.reset()
    s = tmp_path / "s.jsonl"
    write_session(s)
    main(["show", str(s), "--visible"])
    err = capsys.readouterr().err
    assert "--show-invisible" in err
    assert "2.0.0" in err


def test_the_old_flag_is_hidden_from_help(capsys):
    from sseint.cli import build_parser
    parser = build_parser()
    text = parser.parse_args(["show", "x"])
    assert hasattr(text, "visible_deprecated")
    sub = [a for a in parser._subparsers._group_actions[0].choices
           if a == "show"]
    assert sub
    help_text = parser._subparsers._group_actions[0] \
        .choices["show"].format_help()
    assert "--show-invisible" in help_text
    assert "--visible " not in help_text
