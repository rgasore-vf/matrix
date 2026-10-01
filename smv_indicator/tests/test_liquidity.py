"""R-LQ-01 à R-LQ-03, R-CA-05."""
from helpers import CLOSES_UP_THEN_DOWN, from_closes, from_ohlc, kinds, run

from smv import BEAR, BULL, Config
from smv.candles import is_doji, is_manipulative, liquidity_signature
from smv.data import from_ohlc as mk


def test_level_status_bos_vs_clean():
    _, log = run(from_closes(CLOSES_UP_THEN_DOWN), pivot_left=1, pivot_right=1)
    lb = {e.data["level"]: e.confirm_index for e in kinds(log, "LIQ_BOS")}
    assert lb["PH:2"] == 6 and lb["PH:7"] == 11 and lb["PL:9"] == 14 and lb["PL:4"] == 16
    assert "PH:11" not in lb


def test_wick_through_level_is_clean_not_intact():
    # écart volontaire avec l'ancien EA : une mèche suffit à retirer le statut « intact »
    rows = [(1, 2, 0.5, 1.5), (1.5, 5, 1.4, 4.5), (4.5, 4.6, 3, 3.2), (3.2, 3.3, 2, 2.5),
            (2.5, 5.2, 2.4, 4.9)]
    _, log = run(from_ohlc(rows), pivot_left=1, pivot_right=1)
    clean = kinds(log, "LIQ_CLEAN")
    assert [(e.data["level"], e.confirm_index) for e in clean] == [("PH:1", 4)]


def test_equal_highs_within_tolerance():
    rows = [(1, 1.5, 0.9, 1.2), (1.2, 2.0, 1.1, 1.8), (1.8, 1.9, 1.3, 1.4), (1.4, 1.9, 1.3, 1.8),
            (1.8, 1.999, 1.7, 1.9), (1.9, 1.95, 1.4, 1.5), (1.5, 1.6, 1.0, 1.1)]
    _, log = run(from_ohlc(rows), pivot_left=1, pivot_right=1, eq_tol_atr=0.1)
    eq = kinds(log, "EQUAL_LEVELS")
    assert len(eq) == 1 and eq[0].data["first"] == "PH:1" and eq[0].data["second"] == "PH:4"
    assert eq[0].price == 2.0 and eq[0].confirm_index == 5
    _, log2 = run(from_ohlc(rows), pivot_left=1, pivot_right=1, eq_tol_atr=0.0001)
    assert kinds(log2, "EQUAL_LEVELS") == []


def test_second_top_above_first_is_a_sweep_not_equal_highs():
    # Cas limite : un 2e sommet qui dépasse le 1er, même d'un cheveu, prend sa liquidité
    # (R-LQ-01) ; le 1er n'est plus intact, il n'y a donc pas d'EQH (R-LQ-03).
    rows = [(1, 1.5, 0.9, 1.2), (1.2, 2.0, 1.1, 1.8), (1.8, 1.9, 1.3, 1.4), (1.4, 1.9, 1.3, 1.8),
            (1.8, 2.001, 1.7, 1.9), (1.9, 1.95, 1.4, 1.5), (1.5, 1.6, 1.0, 1.1)]
    _, log = run(from_ohlc(rows), pivot_left=1, pivot_right=1, eq_tol_atr=0.1)
    assert kinds(log, "EQUAL_LEVELS") == []
    assert [(e.data["level"], e.confirm_index) for e in kinds(log, "LIQ_CLEAN")][0] == ("PH:1", 4)


def test_candle_classifiers():
    c = Config()
    b = mk([(1.0, 2.0, 0.0, 1.05), (2.0, 2.0, 1.0, 1.0), (1.0, 3.0, 0.9, 1.4), (0.0, 0.0, 0.0, 0.0)])
    assert is_doji(b[0], c) and not is_doji(b[1], c)
    assert is_doji(b[3], c)  # range nul
    assert is_manipulative(b[1], BULL, c, None)       # baissière pleine -> BM d'une demande
    assert not is_manipulative(b[1], BEAR, c, None)   # mauvaise couleur pour une offre
    assert liquidity_signature(b[2], c) == BULL       # haussière, mèche haute 1.6 / 2.1
    assert liquidity_signature(b[3], c) == 0


def test_signature_creates_target_level():
    rows = [(1, 1.2, 0.9, 1.1), (1.1, 2.5, 1.0, 1.4), (1.4, 1.5, 1.2, 1.3), (1.3, 2.6, 1.2, 2.55)]
    _, log = run(from_ohlc(rows), pivot_left=1, pivot_right=1)
    sig = kinds(log, "LIQ_SIGNATURE")
    assert [(e.confirm_index, e.direction, e.price) for e in sig] == [(1, BULL, 2.5)]
    taken = [e for e in kinds(log, "LIQ_BOS") if e.data["level"] == "LS:1"]
    assert [e.confirm_index for e in taken] == [3]
