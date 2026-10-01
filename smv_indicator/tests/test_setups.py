"""R-SE-01 à R-SE-03, R-GS-03, §9 : cycle de vie des setups.

Les règles de qualification sont testées en isolant SetupTracker : le contexte de bougies
est réel, la structure, la liquidité et la consolidation sont remplacées par des objets
minimaux dont l'état est fixé à la main. L'intégration complète est couverte par
test_no_lookahead.py (les setups sont actifs dans la configuration par défaut).
"""
from types import SimpleNamespace

from helpers import from_ohlc, kinds

from smv import BEAR, BULL, Config, Engine
from smv.context import Context
from smv.data import synthetic
from smv.ranges import Range, RangeTracker
from smv.setups import SetupTracker
from smv.types import Event, Kind

FLAT = (10.0, 10.2, 9.8, 10.0)


class FakeLiquidity:
    def __init__(self, highs=(), lows=()):
        self.highs = [SimpleNamespace(price=p, lid=f"H{p}") for p in highs]
        self.lows = [SimpleNamespace(price=p, lid=f"L{p}") for p in lows]

    def intact_targets(self, entry, d):
        if d == BULL:
            return sorted((x for x in self.highs if x.price > entry), key=lambda x: x.price)
        return sorted((x for x in self.lows if x.price < entry), key=lambda x: -x.price)


def tracker(rows, trend=BULL, liq=None, rng=None, **cfg):
    c = Config(**cfg)
    ctx = Context(c.atr_len)
    for b in from_ohlc(rows):
        ctx.append(b)
    ranges = RangeTracker(c, ctx)
    ranges.current = rng
    st = SimpleNamespace(trend=trend)
    return SetupTracker(c, ctx, st, liq or FakeLiquidity(highs=(11.0, 12.0), lows=(8.0,)), ranges)


def zone(i, d, proximal, distal, source=Kind.BOS_CONTINUATION):
    return Event(Kind.ZONE, i, i - 1, d, proximal, f"Z:{i}",
                 {"proximal": proximal, "distal": distal, "source": source})


def concept_ready(t, i):
    """Inducement haussier révélé puis pris en tendance haussière."""
    t.on_events(i, [Event(Kind.INDUCEMENT, i, i - 1, 0, 9.9, "IDM:PL:1",
                          {"level_ref": "PL:1", "side": "L", "trend": BULL})])
    t.on_events(i, [Event(Kind.LIQ_CLEAN, i, i, 0, 9.9, "LC:PL:1", {"level": "PL:1"})])


def test_concept_setup_lifecycle_to_target():
    rows = [FLAT] * 20 + [(10.3, 10.6, 10.05, 10.5), (10.5, 11.2, 10.4, 11.1)]
    t = tracker(rows)
    concept_ready(t, 19)
    out = t.on_events(19, [zone(19, BULL, 10.1, 9.9)])
    s = kinds(out, "SETUP")[0]
    assert s.data["type"] == "CONCEPT" and s.data["rejected"] is None
    assert s.data["targets"] == [11.0, 12.0] and s.data["rr"] == [4.5, 9.5]
    assert t.update(19) == []                          # créé sur 19 : suivi à partir de 20
    trig = t.update(20)
    assert [e.kind for e in trig] == ["SETUP_TRIGGERED"]
    closed = t.update(21)
    assert closed[0].kind == "SETUP_CLOSED" and closed[0].data["reason"] == "target1"
    assert closed[0].data["r"] == 4.5 and t.active == []


def test_stop_wins_when_stop_and_target_on_same_bar():
    rows = [FLAT] * 20 + [(10.3, 11.5, 9.5, 10.0)]
    t = tracker(rows)
    concept_ready(t, 19)
    t.on_events(19, [zone(19, BULL, 10.1, 9.9)])
    out = t.update(20)
    assert [e.kind for e in out] == ["SETUP_TRIGGERED", "SETUP_CLOSED"]
    assert out[1].data["reason"] == "stop" and out[1].data["r"] == -1.0


def test_concept_requires_inducement_taken_in_trend():
    t = tracker([FLAT] * 20)
    assert kinds(t.on_events(19, [zone(19, BULL, 10.1, 9.9)]), "SETUP") == []
    # inducement révélé dans une tendance baissière : ne qualifie pas un achat
    t2 = tracker([FLAT] * 20, trend=BULL)
    t2.on_events(19, [Event(Kind.INDUCEMENT, 19, 18, 0, 9.9, "IDM:PL:1",
                            {"level_ref": "PL:1", "side": "L", "trend": BEAR})])
    t2.on_events(19, [Event(Kind.LIQ_CLEAN, 19, 19, 0, 9.9, "LC:PL:1", {"level": "PL:1"})])
    assert kinds(t2.on_events(19, [zone(19, BULL, 10.1, 9.9)]), "SETUP") == []
    # un BOS de changement ne crée pas de setup « concept »
    t3 = tracker([FLAT] * 20)
    concept_ready(t3, 19)
    assert kinds(t3.on_events(19, [zone(19, BULL, 10.1, 9.9, Kind.BOS_CHANGE)]), "SETUP") == []


def test_rejections_are_logged_but_not_tracked():
    t = tracker([FLAT] * 20, liq=FakeLiquidity(highs=(), lows=()))
    concept_ready(t, 19)
    s = kinds(t.on_events(19, [zone(19, BULL, 10.1, 9.9)]), "SETUP")[0]
    assert s.data["rejected"] == "no_target" and t.active == []
    t = tracker([FLAT] * 20)                            # ATR ≈ 0,4 ; risque 2,0 > 2,5 x 0,4
    concept_ready(t, 19)
    s = kinds(t.on_events(19, [zone(19, BULL, 10.1, 8.1)]), "SETUP")[0]
    assert s.data["rejected"] == "sl_too_wide"


def test_expiry_not_triggered_and_trend_change():
    rows = [FLAT] * 20 + [(10.5, 10.7, 10.3, 10.6)] * 4
    t = tracker(rows, setup_expiry_bars=2)
    concept_ready(t, 19)
    t.on_events(19, [zone(19, BULL, 10.1, 9.9)])
    assert t.update(20) == []
    exp = t.update(21)
    assert exp[0].kind == "SETUP_EXPIRED" and exp[0].data["reason"] == "not_triggered"
    t = tracker(rows)
    concept_ready(t, 19)
    t.on_events(19, [zone(19, BULL, 10.1, 9.9)])
    out = t.on_events(20, [Event(Kind.BOS_CHANGE, 20, 15, BEAR, 9.0, "B", {})])
    assert out[0].kind == "SETUP_EXPIRED" and out[0].data["reason"] == "trend_change"


def test_golden_needs_sweep_on_opposite_bound():
    rng = Range("R:5", BEAR, 9.0, 11.0, 5, "PL:3")
    t = tracker([FLAT] * 20, rng=rng)
    # prise de la borne HAUTE : ne qualifie pas un achat
    t.on_events(12, [Event(Kind.RANGE_SWEEP, 12, 12, BULL, 11.1, "RS", {"range": "R:5", "side": "H"})])
    assert kinds(t.on_events(19, [zone(19, BULL, 10.1, 9.9, Kind.BOS_CHANGE)]), "SETUP") == []
    rng.sweeps["L"] = 1
    t.on_events(15, [Event(Kind.RANGE_SWEEP, 15, 15, BEAR, 8.9, "RS", {"range": "R:5", "side": "L"})])
    s = kinds(t.on_events(19, [zone(19, BULL, 10.1, 9.9, Kind.BOS_CHANGE)]), "SETUP")[0]
    assert s.data["type"] == "GOLDEN" and s.data["label"] == "STB"
    assert s.data["deadline"] == 19 + Config().test_max_bars


def test_golden_allowed_on_bar_that_closes_range_only():
    rng = Range("R:5", BEAR, 9.0, 11.0, 5, "PL:3")
    rng.sweeps["L"] = 2
    t = tracker([FLAT] * 25, rng=rng)
    t.on_events(15, [Event(Kind.RANGE_SWEEP, 15, 15, BEAR, 8.9, "RS", {"range": "R:5", "side": "L"})])
    rng.closed, rng.exit_index = True, 19
    s = kinds(t.on_events(19, [zone(19, BULL, 10.1, 9.9, Kind.BOS_CHANGE)]), "SETUP")[0]
    assert s.data["label"] == "SPRING"
    assert kinds(t.on_events(22, [zone(22, BULL, 10.1, 9.9, Kind.BOS_CHANGE)]), "SETUP") == []


def test_engine_setups_are_consistent_on_synthetic_data():
    log = Engine(Config()).run(synthetic(4000, seed=3))
    created = {e.data["setup"]: e for e in kinds(log, "SETUP") if e.data["rejected"] is None}
    assert created
    seen = {}
    for e in log:
        if e.kind in ("SETUP_TRIGGERED", "SETUP_CLOSED", "SETUP_EXPIRED"):
            sid = e.data["setup"]
            assert sid in created and e.confirm_index > created[sid].confirm_index
            seen.setdefault(sid, []).append(e.kind)
    for sid, seq in seen.items():
        assert seq in (["SETUP_EXPIRED"], ["SETUP_TRIGGERED", "SETUP_CLOSED"], ["SETUP_TRIGGERED"]), seq
    assert Engine(Config(enable_setups=False)).run(synthetic(500, seed=3)) and \
        not kinds(Engine(Config(enable_setups=False)).run(synthetic(500, seed=3)), "SETUP")


def test_target_not_counted_on_trigger_bar():
    # La bougie 20 touche l'entrée ET la cible : l'ordre intra-bougie est inconnu, donc pas de
    # sortie gagnante sur cette bougie ; la cible compte à la bougie 21.
    rows = [FLAT] * 20 + [(10.3, 11.5, 10.05, 10.4), (10.4, 11.2, 10.3, 11.0)]
    t = tracker(rows)
    concept_ready(t, 19)
    t.on_events(19, [zone(19, BULL, 10.1, 9.9)])
    assert [e.kind for e in t.update(20)] == ["SETUP_TRIGGERED"]
    out = t.update(21)
    assert out[0].data["reason"] == "target1" and out[0].data["bars_in_trade"] == 1


def test_golden_schema_only_rejects_counter_schema_trades():
    # Consolidation après une tendance baissière (accumulation attendue) : un achat après une
    # prise basse est dans le schéma ; une vente après une prise haute (UA) ne l'est pas.
    rng = Range("R:5", BEAR, 9.0, 11.0, 5, "PL:3")
    rng.sweeps["H"] = 1
    rng.sweeps["L"] = 1
    for schema_only, expected in ((False, ["GOLDEN", "GOLDEN"]), (True, ["GOLDEN"])):
        t = tracker([FLAT] * 20, rng=rng, liq=FakeLiquidity(highs=(11.0,), lows=(8.0,)),
                    golden_schema_only=schema_only)
        t.on_events(15, [Event(Kind.RANGE_SWEEP, 15, 15, BULL, 11.1, "RS", {"range": "R:5", "side": "H"}),
                         Event(Kind.RANGE_SWEEP, 15, 15, BEAR, 8.9, "RS", {"range": "R:5", "side": "L"})])
        got = kinds(t.on_events(19, [zone(19, BULL, 10.1, 9.9, Kind.BOS_CHANGE),
                                     zone(19, BEAR, 9.9, 10.1, Kind.BOS_CHANGE)]), "SETUP")
        assert [e.data["type"] for e in got] == expected
        if schema_only:
            assert got[0].direction == BULL and got[0].data["label"] == "STB"


def test_breakeven_armed_at_close_and_active_next_bar():
    # entrée 10,1 ; stop 9,9 (risque 0,2) ; be_at_r = 1 -> armé quand le plus haut atteint 10,3
    rows = [FLAT] * 20 + [(10.3, 10.4, 10.05, 10.2),   # 20 : déclenchement
                          (10.2, 10.35, 10.15, 10.3),  # 21 : MFE 1,25 R -> break-even armé
                          (10.3, 10.3, 10.0, 10.05)]   # 22 : retour sous l'entrée -> sortie à 0 R
    t = tracker(rows, be_at_r=1.0)
    concept_ready(t, 19)
    t.on_events(19, [zone(19, BULL, 10.1, 9.9)])
    assert [e.kind for e in t.update(20)] == ["SETUP_TRIGGERED"]
    assert t.update(21) == []
    out = t.update(22)
    assert out[0].data["reason"] == "breakeven" and out[0].data["r"] == 0.0
    # sans l'option, la même bougie 22 ne touche pas le stop initial : le trade reste ouvert
    t2 = tracker(rows)
    concept_ready(t2, 19)
    t2.on_events(19, [zone(19, BULL, 10.1, 9.9)])
    t2.update(20); t2.update(21)
    assert t2.update(22) == [] and len(t2.active) == 1


def test_premium_discount_filter():
    from smv.mtf import premium_discount_ok
    up = {"trend": BULL, "prot": (100.0, 3), "leg_ext": (120.0, 9)}
    assert premium_discount_ok({"structure": up}, 105.0, BULL)
    assert not premium_discount_ok({"structure": up}, 115.0, BULL)
    assert premium_discount_ok({"structure": up}, 115.0, BEAR)
    assert not premium_discount_ok(None, 105.0, BULL)
    assert not premium_discount_ok({"structure": {"trend": 0, "prot": None, "leg_ext": None}}, 105.0, BULL)
