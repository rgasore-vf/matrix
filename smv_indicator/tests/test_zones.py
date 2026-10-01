"""R-OD-01 à R-OD-05, sur la série de référence (voir test_structure.py).

Bougie 9 : open 12, close 11.5 (baissière, corps = range) -> BM et BQA confondues.
Zone de demande créée au BOS de continuation (bougie 11) : [11.5, 12].
Bougie 11 : open 12, close 14 (haussière pleine) -> BM et BQA de la zone d'offre créée
au BOS de changement (bougie 14) : [12, 14].
"""
from helpers import CLOSES_UP_THEN_DOWN, from_closes, from_ohlc, kinds, run

from smv import BEAR, BULL, Config
from smv.context import Context
from smv.zones import ZoneBook


def test_zones_from_bos_origins():
    _, log = run(from_closes(CLOSES_UP_THEN_DOWN), pivot_left=1, pivot_right=1)
    z = kinds(log, "ZONE")
    got = [(e.confirm_index, e.direction, e.data["proximal"], e.data["distal"], e.data["bqa_index"],
            e.data["bm_index"], e.data["decisional"]) for e in z]
    assert got == [(11, BULL, 12, 11.5, 9, 9, False), (14, BEAR, 12, 14, 11, 11, True)]


def test_zone_broken_creates_breaker():
    _, log = run(from_closes(CLOSES_UP_THEN_DOWN), pivot_left=1, pivot_right=1)
    zb = kinds(log, "ZONE_BROKEN")
    assert [(e.confirm_index, e.data["zone"]) for e in zb][0] == (14, "ZD:9:11")
    br = kinds(log, "BREAKER")
    assert br and br[0].direction == BEAR and br[0].data["proximal"] == 11.5 and br[0].data["distal"] == 12


def _book(rows, **cfg):
    c = Config(**cfg)
    ctx = Context(c.atr_len)
    for b in from_ohlc(rows):
        ctx.append(b)
    return ZoneBook(c, ctx)


def test_bm_is_previous_bar_when_bqa_not_full():
    rows = [
        (10.0, 10.2, 9.8, 10.0),
        (10.0, 10.0, 9.0, 9.1),   # 1 : baissière pleine (BM)
        (9.1, 9.3, 8.8, 9.2),     # 2 : BQA (plus bas), petit corps haussier
        (9.2, 10.5, 9.2, 10.4),   # 3 : départ
    ]
    z = _book(rows).build(BULL, 2, 3, "BOS_CONTINUATION", False, True)
    assert z.bm_index == 1 and z.distal == 8.8 and z.proximal == 10.0  # haut du corps de la BM


def test_zone_proximal_wick_option():
    rows = [
        (10.0, 10.0, 9.8, 10.0),
        (9.9, 10.3, 9.0, 9.1),    # BM baissière : corps 0.8 / range 1.3 ≈ 0.62 >= 0.6
        (9.1, 9.3, 8.8, 9.2),
        (9.2, 10.5, 9.2, 10.4),
    ]
    zb = _book(rows, bm_body_min=0.6).build(BULL, 2, 3, "BOS_CONTINUATION", False, True)
    zw = _book(rows, bm_body_min=0.6, zone_proximal="wick").build(BULL, 2, 3, "BOS_CONTINUATION", False, True)
    # avec le seuil par défaut (0,7), cette bougie (corps 62 %) n'est pas une BM
    assert _book(rows).build(BULL, 2, 3, "BOS_CONTINUATION", False, True).bm_index is None
    assert zb.proximal == 9.9 and zw.proximal == 10.3


def test_no_bm_falls_back_to_bqa_candle():
    rows = [
        (10.0, 10.2, 9.8, 10.0),
        (10.0, 10.1, 9.5, 9.9),   # pas pleine
        (9.9, 10.0, 9.0, 9.95),   # BQA, haussière
        (9.95, 10.5, 9.9, 10.4),
    ]
    z = _book(rows).build(BULL, 2, 3, "BOS_CONTINUATION", False, True)
    assert z.bm_index is None and z.proximal == 10.0 and z.distal == 9.0


def test_touch_episodes_counted_once_per_visit():
    # Après la zone [11.5, 12] (créée bougie 11), le prix revient deux fois dans la zone.
    bars = from_closes(CLOSES_UP_THEN_DOWN[:12])
    rows = [(b.open, b.high, b.low, b.close) for b in bars]
    rows += [
        (14, 14, 11.9, 12.5),    # 12 : touche (épisode 1)
        (12.5, 12.6, 11.8, 12.2),  # 13 : toujours dedans, pas de nouvelle touche
        (12.2, 13.5, 12.2, 13.4),  # 14 : sort
        (13.4, 13.4, 11.95, 12.6),  # 15 : touche (épisode 2)
    ]
    _, log = run(from_ohlc(rows), pivot_left=1, pivot_right=1)
    t = [e for e in kinds(log, "ZONE_TOUCH") if e.data["zone"] == "ZD:9:11"]
    assert [(e.confirm_index, e.data["touch"]) for e in t] == [(12, 1), (15, 2)]


def test_odf_link_when_new_bqa_retests_previous_zone():
    # Deux BOS de continuation haussiers successifs ; la BQA du 2e retest la zone du 1er.
    closes = [10, 11, 12, 11, 10, 11, 12.5, 13, 12, 11.5, 12, 14, 13, 11.8, 12.5, 15]
    _, log = run(from_closes(closes), pivot_left=1, pivot_right=1)
    zones = kinds(log, "ZONE")
    odf = kinds(log, "ODF_LINK")
    assert len(zones) == 2
    assert len(odf) == 1 and odf[0].data["chain_len"] == 2 and odf[0].data["is_odf"]
