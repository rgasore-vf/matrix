"""R-ST-02 / R-ST-03."""
from helpers import from_ohlc, kinds, run


def bars_from_highs(highs):
    # bougies neutres : open = close = high - 0.5, low = high - 1
    return from_ohlc([(h - 0.5, h, h - 1, h - 0.5) for h in highs])


def test_pivot_high_confirmed_after_right_bars():
    _, log = run(bars_from_highs([1, 2, 3, 2, 1, 2, 5, 4, 3]), pivot_left=2, pivot_right=2)
    ph = kinds(log, "PIVOT_HIGH")
    assert [(e.anchor_index, e.confirm_index, e.price) for e in ph] == [(2, 4, 3), (6, 8, 5)]
    assert ph[0].data["label"] == ""
    assert ph[1].data["label"] == "HH"


def test_equal_highs_produce_single_pivot_on_first():
    _, log = run(bars_from_highs([1, 3, 3, 1, 1]), pivot_left=1, pivot_right=2)
    ph = kinds(log, "PIVOT_HIGH")
    assert [e.anchor_index for e in ph] == [1]


def test_no_pivot_without_enough_left_bars():
    _, log = run(bars_from_highs([5, 1, 1, 1]), pivot_left=1, pivot_right=1)
    assert kinds(log, "PIVOT_HIGH") == []


def test_labels_lh_and_ll():
    highs = [1, 5, 1, 4, 1]
    _, log = run(bars_from_highs(highs), pivot_left=1, pivot_right=1)
    ph = kinds(log, "PIVOT_HIGH")
    assert [e.data["label"] for e in ph] == ["", "LH"]
