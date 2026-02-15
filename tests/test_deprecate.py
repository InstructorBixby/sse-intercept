import io

from sseint import deprecate


def test_warns_once_per_process():
    deprecate.reset()
    err = io.StringIO()
    deprecate.warn("--old", "--new", removed_in="2.0.0", err=err)
    deprecate.warn("--old", "--new", removed_in="2.0.0", err=err)
    assert err.getvalue().count("deprecated") == 1


def test_the_message_names_the_replacement_and_the_removal():
    deprecate.reset()
    err = io.StringIO()
    deprecate.warn("--old", "--new", removed_in="2.0.0", err=err)
    text = err.getvalue()
    assert "--new" in text
    assert "2.0.0" in text


def test_two_different_names_both_warn():
    deprecate.reset()
    err = io.StringIO()
    deprecate.warn("--a", "--x", removed_in="2.0.0", err=err)
    deprecate.warn("--b", "--y", removed_in="2.0.0", err=err)
    assert err.getvalue().count("deprecated") == 2
