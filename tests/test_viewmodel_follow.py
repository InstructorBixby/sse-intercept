from sseint.decoders.sse import SSEDecoder
from sseint.session import Exchange
from sseint.viewmodel import ViewModel


def many(count):
    ex = Exchange({"ex": 1, "host": "h", "method": "GET",
                   "path": "/s", "status": "HTTP/1.1 200 OK",
                   "decoder": "sse"})
    raw = b"".join(f"data: f{i}\n\n".encode() for i in range(count))
    d = SSEDecoder()
    ex.frames = d.feed(raw) + d.close()
    return ex


def test_filtering_cancels_follow():
    vm = ViewModel([many(50)], height=10)
    vm.visible()
    assert vm.follow
    vm.set_filter(text="f4")
    assert vm.follow is False


def test_the_selection_stays_on_screen_after_filtering():
    vm = ViewModel([many(50)], height=10)
    vm.move(-40)                      # look at something near the top
    seq = vm.current[0].seq
    vm.set_filter(text="f")           # matches everything
    assert any(f.seq == seq for f, _ in vm.visible())


def test_follow_pins_the_tail_and_selects_it():
    vm = ViewModel([many(50)], height=10)
    rows = vm.visible()
    assert rows[-1][0].seq == 50
    assert vm.current[0].seq == 50


def test_selection_is_clamped_when_the_filter_empties_the_list():
    vm = ViewModel([many(50)], height=10)
    vm.move(-10)
    vm.set_filter(text="nothing matches this")
    assert vm.visible() == []
    assert vm.current is None
