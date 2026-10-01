"""Études avec issue future (calibrage et tests d'hypothèses du dépôt), avec modèle nul explicite.

Les issues sont mesurées APRÈS la confirmation des événements (aucun biais d'anticipation dans
le signal ; l'issue regarde le futur par construction, c'est son rôle).

Usage : python research/study_outcomes.py > research/results_outcomes.json
"""
from __future__ import annotations

import json
import math
import os
import random
import sys
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from marketdata import load  # noqa: E402
from smv import Config, Engine  # noqa: E402
from smv.context import Context  # noqa: E402

SYMS = ("EURUSD", "XAUUSD")


def atr_series(bars, n=14):
    ctx = Context(n)
    for b in bars:
        ctx.append(b)
    return ctx.atr


def wilson(k, n):
    if n == 0:
        return (None, None)
    p = k / n
    z = 1.96
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(c - h, 3), round(c + h, 3))


# ---------------------------------------------------------------- zones (Q-02, Q-03, Q-05, Q-06)
def zone_race(bars, atr, z, touch_i, k=1.0, horizon=300):
    """Après la première touche : le prix atteint-il proximal + k*ATR (sens de la zone) avant une
    clôture au-delà du bord distal ? Retourne (succès, attendu sous marche aléatoire sans dérive)."""
    d = z["direction"]
    prox, dist = z["proximal"], z["distal"]
    a = atr[touch_i]
    tgt = prox + d * k * a
    h = abs(prox - dist)
    for j in range(touch_i, min(len(bars), touch_i + horizon)):
        b = bars[j]
        if (d == 1 and b.close < dist) or (d == -1 and b.close > dist):
            return 0, h / (h + k * a)
        if j > touch_i and ((d == 1 and b.high >= tgt) or (d == -1 and b.low <= tgt)):
            return 1, h / (h + k * a)
    return None, None


def study_zones(bars, cfg):
    atr = atr_series(bars)
    log = Engine(cfg).run(bars)
    zones = {e.ref: dict(e.data, direction=e.direction, confirm=e.confirm_index) for e in log
             if e.kind == "ZONE"}
    first_touch = {}
    for e in log:
        if e.kind == "ZONE_TOUCH" and e.data["zone"] in zones and e.data["zone"] not in first_touch:
            first_touch[e.data["zone"]] = e.confirm_index
    groups = defaultdict(lambda: [0, 0, 0.0])
    for zid, z in zones.items():
        t = first_touch.get(zid)
        if t is None:
            continue
        ok, exp = zone_race(bars, atr, z, t)
        if ok is None:
            continue
        keys = ["all", f"source={z['source']}", f"bm={'yes' if z['bm_index'] is not None else 'no'}",
                f"doji_sig={z['doji_signature']}"]
        hh = abs(z["proximal"] - z["distal"]) / atr[z["confirm"]]
        keys.append("height<1atr" if hh < 1 else "height1-2atr" if hh < 2 else "height>=2atr")
        for kk in keys:
            g = groups[kk]
            g[0] += ok
            g[1] += 1
            g[2] += exp
    return {k: {"n": n, "success": round(s / n, 3), "ci95": wilson(s, n), "null_expected": round(e / n, 3),
                "excess": round(s / n - e / n, 3)} for k, (s, n, e) in sorted(groups.items())}


# ---------------------------------------------------------------- structure A vs B (Q-01)
def study_structure(bars, mode):
    atr = atr_series(bars)
    log = Engine(Config(major_mode=mode)).run(bars)
    changes = [e for e in log if e.kind == "BOS_CHANGE"]
    conts = [e for e in log if e.kind == "BOS_CONTINUATION"]
    follow = 0
    fwd = []
    for a, b in zip(changes, changes[1:] + [None]):
        end = b.confirm_index if b else len(bars)
        if any(a.confirm_index < c.confirm_index < end and c.direction == a.direction for c in conts):
            follow += 1
        j = a.confirm_index + 20
        if j < len(bars):
            fwd.append(a.direction * (bars[j].close - bars[a.confirm_index].close) / atr[a.confirm_index])
    durations = [b.confirm_index - a.confirm_index for a, b in zip(changes, changes[1:])]
    durations.sort()
    return {"bos_change": len(changes), "bos_cont": len(conts),
            "follow_through": round(follow / max(1, len(changes)), 3),
            "follow_ci95": wilson(follow, len(changes)),
            "median_trend_bars": durations[len(durations) // 2] if durations else None,
            "mean_fwd20_atr": round(sum(fwd) / max(1, len(fwd)), 3), "n_fwd": len(fwd)}


# ---------------------------------------------------------------- EQH/EQL et inducement (Q-07)
def study_liquidity(bars, horizon=200):
    atr = atr_series(bars)
    log = Engine(Config()).run(bars)
    taken = {}
    for e in log:
        if e.kind in ("LIQ_CLEAN", "LIQ_BOS"):
            taken[e.data["level"]] = e.confirm_index
    eq_known_at = {}
    for e in log:
        if e.kind == "EQUAL_LEVELS":
            for ref in (e.data["first"], e.data["second"]):
                eq_known_at.setdefault(ref, e.confirm_index)
    idm_ids = {e.data["level_ref"]: e.confirm_index for e in log if e.kind == "INDUCEMENT"}
    groups = defaultdict(lambda: [0, 0])
    for e in log:
        if e.kind != "LIQ_LEVEL" or e.data["source"] != "PIVOT":
            continue
        c = e.confirm_index
        t = taken.get(e.ref)
        reveal = eq_known_at.get(e.ref)
        # A later EQ reveal starts a NEW risk set at that reveal. It cannot
        # retrospectively turn the original ordinary level into an EQ signal.
        exposures = [(c, reveal is not None and reveal <= c, True)]
        if reveal is not None and reveal > c:
            exposures.append((reveal, True, False))
        for known, is_eq, original in exposures:
            if known + horizon >= len(bars) or atr[known] <= 0 or (t is not None and t <= known):
                continue
            dist = abs(bars[known].close - e.price) / atr[known]
            dbin = "d<1" if dist < 1 else "d1-3" if dist < 3 else "d>=3"
            hit = int(t is not None and known < t <= known + horizon)
            keys = [f"eq={is_eq}|{dbin}"] + ([f"all|{dbin}"] if original else [])
            for kk in keys:
                groups[kk][0] += hit
                groups[kk][1] += 1
    # inducement : niveau pris dans l'horizon après le BOS qui le révèle, vs pivots de même côté
    for ref, ci in idm_ids.items():
        if ci + horizon >= len(bars):
            continue
        t = taken.get(ref)
        if t is not None and t <= ci:
            continue  # déjà pris avant d'être révélé (rare)
        hit = int(t is not None and t - ci <= horizon)
        groups["inducement_after_reveal"][0] += hit
        groups["inducement_after_reveal"][1] += 1
    return {k: {"n": n, "taken_within_h": round(s / n, 3), "ci95": wilson(s, n)}
            for k, (s, n) in sorted(groups.items())}


# ---------------------------------------------------------------- fenêtre mensuelle (Q-09)
def month_paths(d1):
    """Segments [26 du mois précédent, fin du mois], prix journaliers (h, l, c) et position du 10."""
    by_month = defaultdict(list)
    for b in d1:
        t = b.t_open
        by_month[(t.year, t.month)].append(b)
        if t.day >= 26:
            key = (t.year + (t.month == 12), 1 if t.month == 12 else t.month + 1)
            by_month[key].append(b)
    out = []
    for key, bs in sorted(by_month.items()):
        y, m = key
        py, pm = (y - 1, 12) if m == 1 else (y, m - 1)
        ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
        start = datetime(py, pm, 26, tzinfo=timezone.utc)
        end = datetime(ny, nm, 1, tzinfo=timezone.utc)
        if not d1 or d1[0].t_open > start or d1[-1].t_close < end:
            continue  # neither truncated first/last month is a complete outcome
        bs = sorted((b for b in bs if start <= b.t_open and b.t_close <= end), key=lambda b: b.t_open)
        if len(bs) < 18:
            continue
        cut = next((i for i, b in enumerate(bs) if (b.t_open.year, b.t_open.month) == key and b.t_open.day >= 10), None)
        if cut is None or cut < 3:
            continue
        out.append((bs, cut))
    return out


def month_stats(paths):
    hold_h = hold_l = either_in = high_in = low_in = 0
    for bs, cut in paths:
        hi = max(range(len(bs)), key=lambda i: bs[i].high)
        lo = min(range(len(bs)), key=lambda i: bs[i].low)
        high_in += hi < cut
        low_in += lo < cut
        either_in += (hi < cut) or (lo < cut)
        wh = max(b.high for b in bs[:cut])
        wl = min(b.low for b in bs[:cut])
        hold_h += all(b.high <= wh for b in bs[cut:])
        hold_l += all(b.low >= wl for b in bs[cut:])
    n = len(paths)
    if n == 0:
        return {"months": 0, "high_in_window": None, "low_in_window": None,
                "either_in_window": None, "window_high_holds": None, "window_low_holds": None}
    return {"months": n, "high_in_window": round(high_in / n, 3), "low_in_window": round(low_in / n, 3),
            "either_in_window": round(either_in / n, 3), "window_high_holds": round(hold_h / n, 3),
            "window_low_holds": round(hold_l / n, 3)}


def month_null(paths, sims=200, seed=0):
    """Modèle nul : rendements journaliers permutés au hasard à l'intérieur de chaque segment
    (même volatilité, ordre aléatoire) ; reconstruction des plus hauts/bas par les écarts relatifs."""
    rng = random.Random(seed)
    if not paths:
        return month_stats([])
    from study_nulls import shuffled
    acc = defaultdict(float)
    for _ in range(sims):
        fake = []
        for bs, cut in paths:
            nb = shuffled(bs, rng.getrandbits(64))
            fake.append((nb, cut))
        s = month_stats(fake)
        for k, v in s.items():
            acc[k] += v / sims
    return {k: round(v, 3) for k, v in acc.items()}


# ---------------------------------------------------------------- rotation / perte d'intensité (Q-08)
def study_rotation(bars, horizon=40):
    atr = atr_series(bars)
    log = Engine(Config()).run(bars)
    piv = sorted([e for e in log if e.kind in ("PIVOT_HIGH", "PIVOT_LOW")], key=lambda e: e.anchor_index)
    alt = []
    for e in piv:
        if alt and alt[-1].kind == e.kind:
            if (e.price > alt[-1].price) if e.kind == "PIVOT_HIGH" else (e.price < alt[-1].price):
                alt[-1] = e
            continue
        alt.append(e)
    changes = [e for e in log if e.kind == "BOS_CHANGE"]
    ch_idx = [(e.confirm_index, e.direction) for e in changes]
    up_legs = []  # (indice de confirmation du sommet, amplitude)
    dn_legs = []
    for a, b in zip(alt, alt[1:]):
        amp = abs(b.price - a.price)
        (up_legs if b.kind == "PIVOT_HIGH" else dn_legs).append((b.confirm_index, amp))
    res = {}
    for name, legs, against in (("up", up_legs, -1), ("down", dn_legs, 1)):
        g = {"decay3": [0, 0], "other": [0, 0]}
        for k in range(2, len(legs)):
            c = legs[k][0]
            decay = legs[k][1] < legs[k - 1][1] < legs[k - 2][1]
            hit = int(any(c < ci <= c + horizon and d == against for ci, d in ch_idx))
            key = "decay3" if decay else "other"
            g[key][0] += hit
            g[key][1] += 1
        res[name] = {k: {"n": n, "change_within_h": round(s / max(1, n), 3), "ci95": wilson(s, n)}
                     for k, (s, n) in g.items()}
    return res


def main():
    out = {}
    for sym in SYMS:
        r = {}
        h1 = load(sym, "h1", "2015-01-01", "2022-01-01")
        m15 = load(sym, "m15", "2019-01-01", "2021-01-01")
        r["structure_h1"] = {m: study_structure(h1, m) for m in ("A", "B")}
        r["structure_m15"] = {m: study_structure(m15, m) for m in ("A", "B")}
        r["zones_h1_bosorigin_bm0.6"] = study_zones(h1, Config(bm_body_min=0.6))
        r["zones_h1_bosorigin_bm0.7"] = study_zones(h1, Config(bm_body_min=0.7))
        r["zones_h1_allpivots"] = study_zones(h1, Config(zones_on="all_pivots"))
        r["zones_m15_bosorigin"] = study_zones(m15, Config())
        r["liquidity_h1"] = study_liquidity(h1)
        r["rotation_h1"] = study_rotation(h1)
        print(f"{sym} done", file=sys.stderr)
        out[sym] = r
    # Fenêtre mensuelle : tous les symboles disponibles en D1 (plus de mois)
    allpaths = []
    per = {}
    for sym in ("EURUSD", "XAUUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "EURJPY",
                "GBPJPY", "EURGBP", "EURCHF", "AUDJPY"):
        try:
            d1 = load(sym, "d1")
        except Exception:
            continue
        p = month_paths(d1)
        per[sym] = month_stats(p)
        allpaths += p
    out["month_window"] = {"per_symbol": per, "pooled": month_stats(allpaths),
                           "null_shuffled_daily": month_null(allpaths)}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
