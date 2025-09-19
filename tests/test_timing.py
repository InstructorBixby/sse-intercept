from sseint.decoders.sse import SSEDecoder
from sseint.timing import analyse, histogram, percentile


def frames(raw: bytes, times):
    d = SSEDecoder()
    fs = d.feed(raw) + d.close()
    for f, t in zip(fs, times):
        f.t = t
    return fs


def test_percentile_edges():
    assert percentile([], 50) is None
    assert percentile([1.0], 95) == 1.0
    assert percentile([1, 2, 3, 4], 50) == 3


def test_first_frame_is_separate_from_the_gaps():
    fs = frames(b"data: a\n\ndata: b\n\ndata: c\n\n",
                [2.0, 2.05, 2.1])
    st = analyse(fs)
    assert st.first_frame_s == 2.0
    assert st.gap_max == 0.05


def test_stalls_are_listed_individually():
    fs = frames(b"data: a\n\ndata: b\n\ndata: c\n\n",
                [0.0, 0.05, 4.0])
    st = analyse(fs, stall_s=1.0)
    assert [s.before_seq for s in st.stalls] == [3]
    assert round(st.stalls[0].gap_s, 2) == 3.95


def test_proxy_added_latency_is_attributed():
    fs = frames(b"data: a\n\ndata: b\n\n", [0.0, 3.0])
    st = analyse(fs, added={2: 2500})
    assert st.added_ms_total == 2500
    assert st.stalls[0].added_ms == 2500


def test_keepalive_interval():
    fs = frames(b": p\n\ndata: a\n\n: p\n\n", [0.0, 5.0, 10.0])
    st = analyse(fs)
    assert st.keepalives == 2
    assert st.keepalive_interval_s == 10.0


def test_comments_are_not_counted_as_frames():
    fs = frames(b": p\n\ndata: a\n\n", [0.0, 1.0])
    assert analyse(fs).frames == 1


def test_histogram_buckets_every_gap():
    fs = frames(b"data: a\n\ndata: b\n\ndata: c\n\n",
                [0.0, 0.02, 3.0])
    lines = histogram(fs)
    counts = [int(line.split()[-1]) for line in lines]
    assert sum(counts) == 2
