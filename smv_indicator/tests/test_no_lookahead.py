"""Contrat anti-repaint / anti look-ahead (STRATEGY_SPEC §0.5, ARCHITECTURE §4).

Pour toute série et toute configuration, les événements produits sur les k premières
bougies sont EXACTEMENT ceux du calcul complet dont confirm_index < k, dans le même ordre.
Si un module lisait une bougie future ou réécrivait le passé, ce test échouerait.
"""
import pytest

from smv import Config, Engine
from smv.data import synthetic

CONFIGS = [
    Config(),
    Config(major_mode="B"),
    Config(pivot_left=1, pivot_right=1, zones_on="all_pivots", zone_proximal="wick"),
    Config(pivot_left=3, pivot_right=3, enable_imbalance=True, enable_sessions=True,
           range_accept_bars=1, bm_range_atr=1.0),
]


@pytest.mark.parametrize("seed", [0, 1, 7])
@pytest.mark.parametrize("cfg", CONFIGS, ids=lambda c: f"{c.major_mode}-{c.pivot_right}-{c.zones_on}")
def test_prefix_invariance(seed, cfg):
    bars = synthetic(900, seed=seed)
    full = Engine(cfg).run(bars)
    for k in (37, 250, 611, 899):
        part = Engine(cfg).run(bars[:k])
        expected = [e.key() for e in full if e.confirm_index < k]
        assert [e.key() for e in part] == expected, f"divergence au préfixe {k}"


@pytest.mark.parametrize("seed", [2, 3])
def test_anchor_never_after_confirm_and_streaming_equals_batch(seed):
    bars = synthetic(600, seed=seed)
    eng = Engine(Config(enable_imbalance=True))
    streamed = []
    for b in bars:
        out = eng.on_bar(b)
        assert all(e.confirm_index == b.index for e in out)
        streamed += out
    batch = Engine(Config(enable_imbalance=True)).run(bars)
    assert [e.key() for e in streamed] == [e.key() for e in batch]
    assert all(e.anchor_index <= e.confirm_index for e in batch)


def test_pivot_lag_equals_right_bars():
    bars = synthetic(500, seed=5)
    for n in (1, 2, 4):
        log = Engine(Config(pivot_left=n, pivot_right=n)).run(bars)
        piv = [e for e in log if e.kind in ("PIVOT_HIGH", "PIVOT_LOW")]
        assert piv and all(e.confirm_index - e.anchor_index == n for e in piv)
