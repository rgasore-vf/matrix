"""Independent arithmetic checks for the research scripts, without market data."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "research"))
import marketdata
import study_nulls
import study_outcomes as outcomes
from smv import Bar, Event, Kind
from smv.context import Context
from smv.data import from_ohlc


def test_equal_classification_is_known_only_from_equal_confirmation(monkeypatch):
    bars = from_ohlc([(10, 11, 9, 10)] * 10)
    log = [Event(Kind.LIQ_LEVEL, 0, 0, 0, 10.5, 'H0', {'source': 'PIVOT'}),
           Event(Kind.LIQ_LEVEL, 5, 4, 0, 10.5, 'H4', {'source': 'PIVOT'}),
           Event(Kind.EQUAL_LEVELS, 5, 0, 0, 10.5, 'EQ', {'first': 'H0', 'second': 'H4'}),
           Event(Kind.LIQ_CLEAN, 6, 0, 1, 10.5, 'LC0', {'level': 'H0'}),
           Event(Kind.LIQ_CLEAN, 6, 4, 1, 10.5, 'LC4', {'level': 'H4'})]
    class JournalFixture:
        def __init__(self, cfg):
            pass
        def run(self, bars):
            return log
    monkeypatch.setattr(outcomes, 'Engine', JournalFixture)
    got = outcomes.study_liquidity(bars, horizon=3)
    # H0 starts as ordinary at 0: its take at 6 is outside [1,3].
    # Both EQ risk sets start at 5: both takes at 6 are inside [6,8].
    assert got['eq=False|d<1']['n'] == 1
    assert got['eq=False|d<1']['taken_within_h'] == 0
    assert got['eq=True|d<1']['n'] == 2
    assert got['eq=True|d<1']['taken_within_h'] == 1


def test_month_measurement_includes_the_last_days_of_the_month():
    start = datetime(2026, 1, 20, tzinfo=timezone.utc)
    bars = []
    for i in range(42):
        t = start + timedelta(days=i)
        hi = 50 if t.date().isoformat() == '2026-02-27' else 11
        bars.append(Bar(i, t, t + timedelta(days=1), 10, hi, 9, 10))
    paths = outcomes.month_paths(bars)
    assert len(paths) == 1
    bs, _ = paths[0]
    assert bs[0].t_open.date().isoformat() == '2026-01-26'
    assert bs[-1].t_open.date().isoformat() == '2026-02-28'
    assert outcomes.month_stats(paths)['window_high_holds'] == 0


def test_null_preserves_gaps_true_range_and_volume():
    bars = from_ohlc([(10, 11, 9, 10), (30, 32, 29, 31),
                      (5, 7, 4, 6), (16, 18, 15, 17)])
    shuffled = study_nulls.shuffled(bars, 4)
    def tr(xs):
        ctx = Context(14)
        for b in xs:
            ctx.append(b)
        return sorted(ctx.tr)
    assert tr(shuffled) == tr(bars)
    assert sum(b.volume for b in shuffled) == sum(b.volume for b in bars)


def test_market_data_does_not_silently_repair_invalid_ohlc(tmp_path, monkeypatch):
    folder = tmp_path / 'EURUSD'
    folder.mkdir()
    (folder / 'EURUSDh1.csv').write_text(
        'time,open,high,low,close,volume\n2026-01-01 00:00,100000,99999,99900,100100,1\n')
    monkeypatch.setattr(marketdata, 'ROOT', str(tmp_path))
    with pytest.raises(ValueError):
        marketdata.load('EURUSD', 'h1')
