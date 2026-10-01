"""R-ST-04 à R-ST-07, R-LQ-05.

Série CLOSES_UP_THEN_DOWN (open = clôture précédente, pas de mèche), pivots n = 1 :
- pivots hauts : 2 (12), 7 (13, HH), 11 (14, HH) ; pivots bas : 4 (10), 9 (11.5, HL)
- bougie 6 : clôture 12.5 > pivot haut 12  -> TREND_INIT haussier, niveau protégé = bas 10 (bougie 4)
- bougie 8 : pivot 7 confirmé, égal à l'extrême de jambe -> ref = 13
- bougie 11 : clôture 14 > 13 -> BOS de continuation ; origine = plus bas [7, 11] = 11.5 (bougie 9)
- lecture A : niveau protégé = 11.5 ; bougie 14 : clôture 11 < 11.5 -> BOS de changement baissier,
  nouveau niveau protégé = plus haut [9, 14] = 14 (bougie 11)
- lecture B : niveau protégé reste 10 ; le pivot bas 9 est émis inducement ; bougie 16 : clôture 9 < 10
"""
from helpers import CLOSES_UP_THEN_DOWN, from_closes, from_ohlc, kinds, run

from smv import BEAR, BULL


def test_reference_series_mode_a():
    _, log = run(from_closes(CLOSES_UP_THEN_DOWN), pivot_left=1, pivot_right=1, major_mode="A")
    init = kinds(log, "TREND_INIT")
    assert [(e.confirm_index, e.direction, e.price, e.data["origin_index"]) for e in init] == [(6, BULL, 12, 4)]
    bos = kinds(log, "BOS_CONTINUATION")
    assert [(e.confirm_index, e.direction, e.price, e.anchor_index, e.data["origin_index"]) for e in bos] == [
        (11, BULL, 13, 7, 9)]
    chg = kinds(log, "BOS_CHANGE")
    assert [(e.confirm_index, e.direction, e.price, e.anchor_index, e.data["origin_index"]) for e in chg] == [
        (14, BEAR, 11.5, 9, 11)]
    assert kinds(log, "INDUCEMENT") == []


def test_reference_series_mode_b():
    _, log = run(from_closes(CLOSES_UP_THEN_DOWN), pivot_left=1, pivot_right=1, major_mode="B")
    assert [e.confirm_index for e in kinds(log, "BOS_CONTINUATION")] == [11]
    idm = kinds(log, "INDUCEMENT")
    assert [(e.confirm_index, e.anchor_index, e.data["level_ref"]) for e in idm] == [(11, 9, "PL:9")]
    chg = kinds(log, "BOS_CHANGE")
    # le niveau protégé est resté 10 (bougie 4) : la clôture 11 ne casse pas, la clôture 9 casse
    assert [(e.confirm_index, e.price) for e in chg] == [(16, 10)]


def test_wick_beyond_reference_is_not_a_bos():
    closes = CLOSES_UP_THEN_DOWN[:11]
    bars = from_closes(closes)
    # bougie 11 : mèche à 14 mais clôture 12.9 < 13 -> pas de BOS, prise de liquidité du pivot 7
    rows = [(b.open, b.high, b.low, b.close) for b in bars] + [(12.0, 14.0, 12.0, 12.9)]
    _, log = run(from_ohlc(rows), pivot_left=1, pivot_right=1)
    assert kinds(log, "BOS_CONTINUATION") == []
    clean = kinds(log, "LIQ_CLEAN")
    assert any(e.data["level"] == "PH:7" and e.confirm_index == 11 for e in clean)


def test_bos_requires_strict_close_beyond_level():
    bars = from_closes(CLOSES_UP_THEN_DOWN[:11])
    rows = [(b.open, b.high, b.low, b.close) for b in bars] + [(12.0, 13.0, 12.0, 13.0)]
    _, log = run(from_ohlc(rows), pivot_left=1, pivot_right=1)
    assert kinds(log, "BOS_CONTINUATION") == []


def test_fail_lower_high_opens_range():
    closes = [10, 11, 12, 11, 10, 11, 12.5, 13, 12, 11.5, 12.6, 12.2, 12.4]
    _, log = run(from_closes(closes), pivot_left=1, pivot_right=1)
    fail = kinds(log, "FAIL")
    assert len(fail) == 1
    f = fail[0]
    assert (f.confirm_index, f.anchor_index, f.direction, f.price) == (11, 10, BEAR, 12.6)
    assert (f.data["climax_index"], f.data["climax_price"]) == (7, 13)
    assert (f.data["ar_index"], f.data["ar_price"]) == (9, 11.5)
    rng = kinds(log, "RANGE_OPEN")
    assert len(rng) == 1 and rng[0].data["low"] == 11.5 and rng[0].data["high"] == 13


def test_protected_sweep_emitted_once():
    closes = CLOSES_UP_THEN_DOWN[:12]  # tendance haussière, protégé = 11.5 après la bougie 11
    bars = from_closes(closes)
    rows = [(b.open, b.high, b.low, b.close) for b in bars]
    rows += [(14, 14, 11.4, 12.0), (12.0, 12.5, 11.3, 12.2)]  # deux mèches sous 11.5 sans clôture
    _, log = run(from_ohlc(rows), pivot_left=1, pivot_right=1)
    sw = kinds(log, "PROTECTED_SWEEP")
    assert [(e.confirm_index, e.price) for e in sw] == [(12, 11.5)]
    assert kinds(log, "BOS_CHANGE") == []
