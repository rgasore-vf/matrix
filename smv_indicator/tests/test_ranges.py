"""R-CE-01, R-CE-02, R-GS-02 (expérimental)."""
from helpers import from_closes, from_ohlc, kinds, run

from smv import BEAR, BULL

# tendance haussière, fail à la bougie 11 -> fourchette [11.5, 13] (contexte distribution)
BASE = [10, 11, 12, 11, 10, 11, 12.5, 13, 12, 11.5, 12.6, 12.2, 12.4]


def base_rows():
    return [(b.open, b.high, b.low, b.close) for b in from_closes(BASE)]


def test_sweeps_are_labelled_by_context_and_counted():
    rows = base_rows() + [
        (12.4, 13.2, 12.3, 12.8),   # 13 : mèche au-dessus de 13 -> UT
        (12.8, 12.9, 12.6, 12.7),   # 14 : retour dans la fourchette (fin d'épisode)
        (12.7, 13.3, 12.6, 12.7),   # 15 : 2e prise haute -> UTAD
        (12.7, 12.8, 11.3, 11.8),   # 16 : mèche sous 11.5 -> MSO (prise de l'AR)
    ]
    _, log = run(from_ohlc(rows), pivot_left=1, pivot_right=1)
    sw = kinds(log, "RANGE_SWEEP")
    assert [(e.confirm_index, e.data["side"], e.data["label_candidate"]) for e in sw] == [
        (13, "H", "UT"), (15, "H", "UTAD"), (16, "L", "MSO")]


def test_exit_requires_acceptance_and_short_excursion_is_a_sweep():
    rows = base_rows() + [
        (12.4, 13.4, 12.3, 13.2),   # 13 : clôture au-dessus (excursion en attente)
        (13.2, 13.3, 12.5, 12.6),   # 14 : retour dedans -> prise de liquidité, pas de sortie
        (12.6, 12.7, 11.0, 11.2),   # 15 : clôture sous 11.5 (1/3)
        (11.2, 11.3, 10.8, 11.0),   # 16 : (2/3)
        (11.0, 11.1, 10.5, 10.6),   # 17 : (3/3) -> sortie baissière validée, ancrée en 15
    ]
    _, log = run(from_ohlc(rows), pivot_left=1, pivot_right=1, range_accept_bars=3)
    sw = kinds(log, "RANGE_SWEEP")
    assert [(e.confirm_index, e.anchor_index, e.data["label_candidate"]) for e in sw] == [(14, 13, "UT")]
    ex = kinds(log, "RANGE_EXIT")
    assert len(ex) == 1
    e = ex[0]
    assert (e.confirm_index, e.anchor_index, e.direction) == (17, 15, BEAR)
    assert e.data["outcome"] == "confirmed" and e.data["wyckoff_type"] == "type2"


def test_invalidated_when_exit_against_expected_direction():
    rows = base_rows() + [(12.4, 13.4, 12.3, 13.3), (13.3, 13.8, 13.2, 13.7), (13.7, 14.0, 13.6, 13.9)]
    _, log = run(from_ohlc(rows), pivot_left=1, pivot_right=1, range_accept_bars=3)
    ex = kinds(log, "RANGE_EXIT")
    assert len(ex) == 1 and ex[0].direction == BULL and ex[0].data["outcome"] == "invalidated"


def test_consecutive_wicks_beyond_bound_are_one_sweep():
    rows = base_rows() + [
        (12.4, 13.2, 12.3, 12.8),   # 13 : début d'épisode au-dessus de 13
        (12.8, 13.1, 12.6, 12.7),   # 14 : toujours au-dessus en mèche -> même épisode
        (12.7, 12.9, 12.5, 12.6),   # 15 : reste dedans
        (12.6, 13.3, 12.5, 12.9),   # 16 : nouvel épisode -> 2e prise
    ]
    _, log = run(from_ohlc(rows), pivot_left=1, pivot_right=1)
    sw = kinds(log, "RANGE_SWEEP")
    assert [(e.confirm_index, e.data["label_candidate"]) for e in sw] == [(13, "UT"), (16, "UTAD")]
