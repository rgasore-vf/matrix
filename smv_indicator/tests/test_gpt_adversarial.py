"""Independent counterexamples. Expected values follow arithmetic and the documented
event contract, rather than a second copy of the production algorithm.
"""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import math
import sys
from pathlib import Path

import pytest

from smv import Bar, Config, Engine, Event, Kind, BULL, BEAR
from smv.context import Context
from smv.data import from_closes, from_ohlc
from smv.mtf import resample
from smv.ranges import Range, RangeTracker
from smv.setups import Setup, SetupTracker
from smv.liquidity import LiquidityBook
from smv.structure import StructureTracker
from smv.pivots import PivotDetector
from render.primitives import build

BASE = [10, 11, 12, 11, 10, 11, 12.5, 13, 12, 11.5, 12]
UTC = timezone.utc


@pytest.mark.parametrize('direction', [BULL, BEAR])
def test_bos_and_old_protected_sweep_are_both_observable(direction):
    # Before bar 11: trend UP, protected 10, reference 13. This outside bar
    # takes 10 in its wick and closes above 13. Neither fact cancels the other.
    rows = [(b.open, b.high, b.low, b.close) for b in from_closes(BASE)]
    rows += [(12, 14, 9, 14)]
    if direction == BEAR:
        rows = [(40-o, 40-l, 40-h, 40-c) for o, h, l, c in rows]
    log = Engine(Config(pivot_left=1, pivot_right=1)).run(from_ohlc(rows))
    assert any(e.kind == Kind.BOS_CONTINUATION and e.confirm_index == 11 and e.direction == direction for e in log)
    assert any(e.kind == Kind.PROTECTED_SWEEP and e.confirm_index == 11 and e.price == (10 if direction == BULL else 30) for e in log)


@pytest.mark.parametrize('direction', [BULL, BEAR])
def test_first_lower_high_after_bos_is_a_fail(direction):
    # Wick high 20 is confirmed on the same close as BOS 12. The new leg
    # starts at bar 12 (low 11), excluding that old pivot. High 18 at bar 13
    # is nevertheless an LH against 20 and must confirm a FAIL at bar 14.
    rows = [(b.open, b.high, b.low, b.close) for b in from_closes(BASE)]
    rows += [(12, 20, 11.8, 12.5), (12.5, 14, 11, 14),
             (14, 18, 12, 17), (17, 17.5, 12, 16)]
    if direction == BEAR:
        rows = [(40-o, 40-l, 40-h, 40-c) for o, h, l, c in rows]
    log = Engine(Config(pivot_left=1, pivot_right=1)).run(from_ohlc(rows))
    assert any(e.kind == (Kind.PIVOT_HIGH if direction == BULL else Kind.PIVOT_LOW) and
               e.anchor_index == 13 and e.data['label'] == ('LH' if direction == BULL else 'HL') for e in log)
    assert any(e.kind == Kind.FAIL and (e.anchor_index, e.confirm_index) == (13, 14) for e in log)


def test_equal_highs_obey_maximum_age():
    highs = [3, 5, 4, 4, 4, 4, 4, 4, 4, 4.999, 4]
    # Strictly decreasing lows prevent unrelated low pivots from masking the bug.
    bars = from_ohlc([(3, h, 2.5 - i * .1, 3) for i, h in enumerate(highs)])
    log = Engine(Config(pivot_left=1, pivot_right=1, eq_max_gap=3)).run(bars)
    assert not [e for e in log if e.kind == Kind.EQUAL_LEVELS]


@pytest.mark.parametrize('rows,expected', [
    ([(10, 10.5, 9.5, 10), (10, 12, 8, 11.5), (11.5, 11.5, 9.5, 10)], [(1, 'L'), (2, 'H')]),
    ([(10, 10.5, 9.5, 10), (10, 12, 9.5, 11.5), (11.5, 11.5, 8, 10)], [(2, 'H'), (2, 'L')]),
])
def test_pending_range_excursion_does_not_hide_other_side(rows, expected):
    ctx = Context(14)
    tracker = RangeTracker(Config(), ctx)
    tracker.current = Range('R:0', BEAR, 9, 11, 0, 'PL:0')
    events = []
    for b in from_ohlc(rows):
        ctx.append(b)
        events += tracker.update(b.index)
    assert [(e.confirm_index, e.data['side']) for e in events if e.kind == Kind.RANGE_SWEEP] == expected


@pytest.mark.parametrize('direction', [BULL, BEAR])
def test_range_simultaneous_sweeps_through_the_whole_engine(direction):
    # This prelude creates a real FAIL/range [11.5,13] in the full pipeline.
    points = [10,11,12,11,10,11,12.5,13,12,11.5,12.6,12.2,12.4]
    rows = [(b.open,b.high,b.low,b.close) for b in from_closes(points)]
    rows += [(12.4,13.4,11.3,13.2), (13.2,13.3,11.6,12.6)]
    if direction == BEAR:
        rows = [(40-o,40-l,40-h,40-c) for o,h,l,c in rows]
    log = Engine(Config(pivot_left=1,pivot_right=1)).run(from_ohlc(rows))
    expected = [(13,'L'),(14,'H')] if direction == BULL else [(13,'H'),(14,'L')]
    assert [(e.confirm_index,e.data['side']) for e in log if e.kind == Kind.RANGE_SWEEP] == expected


def test_resample_rejects_a_bar_that_contains_future_of_its_bucket():
    # A 15-minute candle cannot disclose its high at minute 7.
    bars = from_ohlc([(10, 99, 9, 11)], timeframe_minutes=15)
    with pytest.raises(ValueError):
        resample(bars, 7)


def test_resample_omits_missing_start_and_missing_middle():
    bars = from_ohlc([(10, 11, 9, 10)] * 8, timeframe_minutes=15)
    assert resample(bars[1:4], 60) == []  # the hour's opening is unknown
    assert resample([bars[0], bars[2], bars[3]], 60) == []  # 00:15 is absent
    assert len(resample(bars[1:], 60)) == 1  # later complete hour still emitted


@pytest.mark.parametrize('field,value', [('open', math.nan), ('high', math.inf), ('low', -math.inf)])
def test_nonfinite_price_rejected_before_context_mutation(field, value):
    ctx = Context(14)
    b = replace(from_ohlc([(10, 11, 9, 10)])[0], **{field: value})
    with pytest.raises(ValueError):
        ctx.append(b)
    assert ctx.bars == [] and ctx.atr == []


def test_duplicate_and_overlapping_bars_rejected():
    b = from_ohlc([(10, 11, 9, 10)])[0]
    ctx = Context(14)
    ctx.append(b)
    with pytest.raises(ValueError):
        ctx.append(replace(b, index=1))
    with pytest.raises(ValueError):
        ctx.append(replace(b, index=1, t_open=b.t_open + timedelta(minutes=5)))


@pytest.mark.parametrize('kw', [{'pivot_left': 1.5}, {'bos_eps': -.1}, {'bos_eps': math.nan},
                               {'eq_tol_atr': math.nan}, {'eq_max_gap': -1}, {'bm_search_back': -1},
                               {'odf_min_len': 0}, {'session_window_min': 0}, {'sl_max_atr': math.inf}])
def test_invalid_configuration_rejected(kw):
    with pytest.raises(ValueError):
        Config(**kw)


def test_event_payload_cannot_change_after_emission():
    payload = {'targets': [11, 12]}
    e = Event(Kind.SETUP, 1, 0, BULL, 10, 'S', payload)
    payload['targets'].append(13)
    assert e.data['targets'] == [11, 12]
    with pytest.raises(TypeError):
        e.data['targets'].append(14)
    with pytest.raises(TypeError):
        e.data['targets'] = []


def test_stop_gap_is_not_reported_as_guaranteed_minus_one_r():
    ctx = Context(14)
    cfg = Config()
    piv = PivotDetector(cfg, ctx)
    t = SetupTracker(cfg, ctx, StructureTracker(cfg, ctx, piv), LiquidityBook(cfg, ctx), RangeTracker(cfg, ctx))
    # A position already open at 10, stop 9, is still open when the next
    # candle opens at 7. Reference execution at that open loses 3 R.
    t.active.append(Setup('S', 'CONCEPT', BULL, 10, 9, [(12, 'H')], 0, 100, 'Z', 'IDM', triggered=1))
    for b in from_ohlc([(10, 11, 9.5, 10), (10, 11, 9.5, 10), (7, 8, 6, 7)]):
        ctx.append(b)
    ev = t.update(2)
    assert len(ev) == 1 and ev[0].data['r'] == -3.0
    assert ev[0].data['execution_price'] == 7


def test_old_inducement_does_not_survive_a_trend_change():
    ctx = Context(14)
    cfg = Config()
    st = StructureTracker(cfg, ctx, PivotDetector(cfg, ctx))
    st.trend = BULL
    t = SetupTracker(cfg, ctx, st, LiquidityBook(cfg, ctx), RangeTracker(cfg, ctx))
    t.on_events(1, [Event(Kind.INDUCEMENT, 1, 0, 0, 9, 'IDM', {'level_ref': 'PL:0', 'trend': BULL})])
    t.on_events(2, [Event(Kind.BOS_CHANGE, 2, 0, BEAR, 9, 'B1')])
    t.on_events(3, [Event(Kind.BOS_CHANGE, 3, 0, BULL, 11, 'B2')])
    t.on_events(4, [Event(Kind.LIQ_CLEAN, 4, 0, BEAR, 9, 'LC', {'level': 'PL:0'})])
    assert t.idm_taken_dir == 0


def test_render_asof_does_not_use_future_status():
    level = Event(Kind.LIQ_LEVEL, 1, 0, 0, 11, 'H', {'source': 'PIVOT'})
    future = Event(Kind.LIQ_CLEAN, 10, 0, BULL, 11, 'LC', {'level': 'H'})
    p = build([level, future], last_index=5)['segments'][0]
    assert p.style == 'liq_intact' and p.x1 == 5


def test_render_range_ends_when_replaced():
    def r(i):
        return Event(Kind.RANGE_OPEN, i, i, BULL, 11, f'R:{i}', {'low': 9, 'high': 11, 'context': 'accumulation?'})
    boxes = build([r(1), r(4)], last_index=8)['boxes']
    assert boxes[0].x1 == 4 and boxes[0].meta['outcome'] == 'replaced'


def test_parity_rejects_nan_event_price():
    sys.path.insert(0, str(Path(__file__).parents[1] / 'tools'))
    import mt5_parity
    e = Event(Kind.TREND_INIT, 0, 0, BULL, 10, 'I')
    assert mt5_parity.compare([e], [(e.kind, 0, 0, BULL, math.nan, 'I', {})])


def test_month_window_does_not_take_extreme_after_window_end():
    # Paris window ends at Jan 9, 23:00 UTC. The second candle straddles
    # that boundary: its high 99 could have occurred AFTER the window.
    a = datetime(2026, 1, 8, tzinfo=UTC)
    bars = [Bar(0, a, a + timedelta(days=1), 1, 2, .5, 1),
            Bar(1, a + timedelta(days=1), a + timedelta(days=2), 1, 99, .1, 1)]
    log = Engine(Config(enable_sessions=True)).run(bars)
    ev = next(e for e in log if e.kind == Kind.MONTH_WINDOW)
    assert ev.data['coverage'] == 'partial' and ev.data['high'] == 2
    assert ev.data['excluded_boundary_bars'] == 1


def test_htf_dst_fold_does_not_make_a_future_close_visible():
    from zoneinfo import ZoneInfo
    from smv.mtf import HtfView
    ny = ZoneInfo('America/New_York')
    opened = datetime(2026, 11, 1, 5, tzinfo=UTC)
    b = Bar(0, opened.astimezone(ny), (opened + timedelta(hours=1)).astimezone(ny), 10, 11, 9, 10)
    # 01:00 fold=0 (05:00 UTC) is before 01:00 fold=1 (06:00 UTC).
    view = HtfView([b])
    assert view.at(opened.astimezone(ny)) is None
    assert view.at(b.t_close)['index'] == 0


def test_paris_session_at_dst_fold_is_marked_at_first_occurrence():
    from zoneinfo import ZoneInfo
    paris = ZoneInfo('Europe/Paris')
    a = datetime(2026, 10, 25, 0, tzinfo=UTC)
    b = Bar(0, a.astimezone(paris), (a + timedelta(hours=1)).astimezone(paris), 10, 11, 9, 10)
    log = Engine(Config(enable_sessions=True, session_mode='repo')).run([b])
    asia = [e for e in log if e.kind == Kind.SESSION and e.data['name'] == 'ASIA']
    assert len(asia) == 1
    assert asia[0].data['start'] == '2026-10-25T02:00:00+02:00'
    assert asia[0].data['end'] == '2026-10-25T02:00:00+01:00'


@pytest.mark.parametrize('gap', [False, True])
def test_month_window_reports_continuous_coverage_only_when_known(gap):
    start = datetime(2026, 1, 25, 23, tzinfo=UTC)  # Jan 26 midnight Paris
    bars = [Bar(i, start + timedelta(hours=i), start + timedelta(hours=i+1), 10, 11, 9, 10)
            for i in range(360)]
    if gap:
        bars = [replace(b, index=j) for j, b in enumerate(b for b in bars if b.index != 120)]
    event = next(e for e in Engine(Config(enable_sessions=True)).run(bars) if e.kind == Kind.MONTH_WINDOW)
    assert event.data['coverage'] == ('partial' if gap else 'complete')


def test_outside_bar_can_confirm_both_pivot_sides():
    log = Engine(Config(pivot_left=1, pivot_right=1)).run(
        from_ohlc([(10,11,9,10), (10,14,6,10), (10,12,8,10)]))
    pivots = [e for e in log if e.kind in (Kind.PIVOT_HIGH, Kind.PIVOT_LOW)]
    assert [(e.kind, e.anchor_index, e.confirm_index) for e in pivots] == [
        (Kind.PIVOT_HIGH,1,2), (Kind.PIVOT_LOW,1,2)]


def test_equal_plateau_anchors_at_first_high():
    log = Engine(Config(pivot_left=1, pivot_right=1)).run(
        from_ohlc([(1,h,0,1) for h in (2,3,3,3,2)]))
    assert [(e.anchor_index, e.confirm_index) for e in log if e.kind == Kind.PIVOT_HIGH] == [(1,2)]


def test_frozen_event_remains_serializable():
    import json
    from dataclasses import asdict
    e = Event(Kind.SETUP, 1, 0, BULL, 10, 'S', {'targets': [11,12]})
    assert json.loads(json.dumps(asdict(e)))['data']['targets'] == [11,12]
