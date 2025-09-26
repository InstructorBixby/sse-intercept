from sseint.decoders.sse import SSEDecoder
from sseint.session import Exchange
from sseint.viewmodel import ViewModel


def exchange(raw: bytes, n=1, ops=None):
    ex = Exchange({"ex": n, "host": "h", "method": "GET",
                   "path": "/s", "status": "HTTP/1.1 200 OK",
                   "decoder": "sse"})
    d = SSEDecoder()
    ex.frames = d.feed(raw) + d.close()
    ex.ops = ops or {}
    return ex


def many(count):
    raw = b"".join(f"data: f{i}\n\n".encode() for i in range(count))
    return exchange(raw)


def test_rows_are_every_frame_by_default():
    vm = ViewModel([exchange(b"data: a\n\n: p\n\n")])
    assert len(vm.rows) == 2


def test_text_filter():
    vm = ViewModel([exchange(b"data: alpha\n\ndata: beta\n\n")])
    vm.filter.text = "alph"
    assert [f.data for f, _ in vm.rows] == ["alpha"]


def test_regex_filter_with_a_bad_pattern_matches_nothing():
    vm = ViewModel([exchange(b"data: a\n\n")])
    vm.filter.text = "("
    vm.filter.regex = True
    assert vm.rows == []


def test_kind_filter_hides_keepalives():
    vm = ViewModel([exchange(b"data: a\n\n: p\n\n")])
    vm.filter.kinds = {"event"}
    assert len(vm.rows) == 1


def test_touched_only():
    ex = exchange(b"data: a\n\ndata: b\n\n", ops={2: ["slow"]})
    vm = ViewModel([ex])
    vm.filter.touched_only = True
    assert [f.seq for f, _ in vm.rows] == [2]


def test_follow_keeps_the_tail_visible():
    vm = ViewModel([many(50)], height=10)
    visible = vm.visible()
    assert [f.seq for f, _ in visible][-1] == 50


def test_moving_leaves_follow_mode_and_scrolls():
    vm = ViewModel([many(50)], height=10)
    vm.visible()
    vm.move(-5)
    assert vm.follow is False
    vm.selected = 0
    vm.move(0)
    assert vm.top == 0


def test_selection_is_clamped_when_the_filter_shrinks_the_list():
    ex = exchange(b"data: a\n\ndata: b\n\ndata: c\n\n")
    vm = ViewModel([ex], height=10)
    vm.move(2)
    vm.filter.text = "a"
    assert vm.current[0].data == "a"


def test_detail_splits_multi_line_data():
    vm = ViewModel([exchange(b"data: one\ndata: two\n\n")])
    detail = vm.detail()
    assert any(line.strip().startswith("data: one") for line in detail)
    assert any("two" in line for line in detail)


def test_exchange_cycling_resets_the_view():
    vm = ViewModel([exchange(b"data: a\n\n"),
                    exchange(b"data: b\n\n", n=2)])
    vm.move(1)
    vm.next_exchange()
    assert vm.index == 1 and vm.top == 0 and vm.selected == 0
