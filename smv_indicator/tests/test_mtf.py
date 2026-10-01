"""R-MTF-01 à R-MTF-03."""
from datetime import timedelta

from smv import BEAR, BULL, Event, Kind
from smv.data import synthetic
from smv.mtf import HtfView, bos_trap_risk, resample


def test_resample_ohlc_and_completeness():
    base = synthetic(10, seed=3, timeframe_minutes=15)
    h = resample(base, 60)
    # 10 bougies de 15 min depuis 00:00 : deux heures complètes, la 3e incomplète est omise
    assert len(h) == 2
    first = base[0:4]
    assert h[0].open == first[0].open and h[0].close == first[-1].close
    assert h[0].high == max(b.high for b in first) and h[0].low == min(b.low for b in first)
    assert h[0].t_close - h[0].t_open == timedelta(hours=1)


def test_htf_view_never_returns_future_state():
    base = synthetic(400, seed=4, timeframe_minutes=15)
    h = resample(base, 60)
    view = HtfView(h)
    assert view.at(base[2].t_close) is None                  # aucune heure close à 00:45
    st = view.at(base[3].t_close)                             # 01:00 : première heure close
    assert st is not None and st["index"] == 0
    st = view.at(base[6].t_close)                             # 01:45 : toujours l'heure 0
    assert st["index"] == 0


def test_bos_trap_risk_rule():
    htf = {"structure": {"trend": BEAR, "prot": (1.20, 5)}}
    ev_up_below = Event(Kind.BOS_CONTINUATION, 10, 8, BULL, 1.15, "x")
    ev_up_above = Event(Kind.BOS_CONTINUATION, 10, 8, BULL, 1.25, "y")
    ev_down = Event(Kind.BOS_CONTINUATION, 10, 8, BEAR, 1.15, "z")
    assert bos_trap_risk(ev_up_below, htf)
    assert not bos_trap_risk(ev_up_above, htf)
    assert not bos_trap_risk(ev_down, htf)
    assert not bos_trap_risk(ev_up_below, None)
