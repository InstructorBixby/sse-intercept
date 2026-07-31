from sseint import __version__
from sseint.version import describe


def test_a_checkout_says_it_is_a_checkout():
    # No _build.py in the tree: the tag job writes it, nothing else.
    assert describe() == f"{__version__} (checkout)"


def test_describe_always_starts_with_the_version():
    assert describe().startswith(__version__)
