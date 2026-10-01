"""Études descriptives de calibrage (sans issue future) : bougies, zones, pivots, EQH/EQL, sessions, ATR.

Usage : python research/study_basic.py > research/results_basic.json
"""
from __future__ import annotations

import json
import os
import statistics as st
import sys
from collections import Counter, defaultdict
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from marketdata import load, pip  # noqa: E402
from smv import Config, Engine  # noqa: E402
from smv.context import Context  # noqa: E402

PARIS = ZoneInfo("Europe/Paris")


def q(xs, ps=(0.1, 0.25, 0.5, 0.75, 0.9)):
    xs = sorted(xs)
    if not xs:
        return {}
    return {f"p{int(p * 100)}": round(xs[min(len(xs) - 1, int(p * len(xs)))], 4) for p in ps}


def atr_series(bars, n=14):
    ctx = Context(n)
    for b in bars:
        ctx.append(b)
    return ctx.atr


def body_ratio_stats(bars):
    return q([b.body_ratio for b in bars if b.range > 0])


def atr_in_pips(sym, bars):
    a = atr_series(bars)
    return q([x / pip(sym) for x in a[100:]])


def hour_profile(bars):
    """Range moyen par heure de Paris (heure d'ouverture de la bougie), normalisé par la moyenne."""
    acc = defaultdict(list)
    for b in bars:
        acc[b.t_open.astimezone(PARIS).hour].append(b.high - b.low)
    means = {h: st.mean(v) for h, v in acc.items()}
    m = st.mean(means.values())
    return {h: round(means[h] / m, 3) for h in sorted(means)}


def pivot_stats(bars, ns=(1, 2, 3, 4, 5)):
    """Amplitude des jambes entre pivots alternés (en ATR) et nombre de pivots par 100 bougies."""
    atr = atr_series(bars)
    out = {}
    for n in ns:
        log = Engine(Config(pivot_left=n, pivot_right=n)).run(bars)
        piv = sorted([e for e in log if e.kind in ("PIVOT_HIGH", "PIVOT_LOW")], key=lambda e: e.anchor_index)
        alt = []
        for e in piv:
            if alt and alt[-1].kind == e.kind:
                better = (e.price > alt[-1].price) if e.kind == "PIVOT_HIGH" else (e.price < alt[-1].price)
                if better:
                    alt[-1] = e
                continue
            alt.append(e)
        legs = [abs(b.price - a.price) / atr[b.anchor_index] for a, b in zip(alt, alt[1:]) if atr[b.anchor_index] > 0]
        out[n] = {"pivots_per_100": round(100 * len(piv) / len(bars), 2), "leg_atr": q(legs),
                  "bars_per_leg": round(len(bars) / max(1, len(alt)), 1)}
    return out


def zone_stats(bars, bm_mins=(0.5, 0.6, 0.7, 0.8)):
    atr = atr_series(bars)
    out = {}
    for bm in bm_mins:
        for prox in ("body", "wick"):
            log = Engine(Config(bm_body_min=bm, zone_proximal=prox)).run(bars)
            zs = [e for e in log if e.kind == "ZONE"]
            h = [abs(e.data["proximal"] - e.data["distal"]) / atr[e.confirm_index] for e in zs]
            with_bm = sum(1 for e in zs if e.data["bm_index"] is not None)
            bm_is_bqa = sum(1 for e in zs if e.data["bm_index"] == e.data["bqa_index"])
            out[f"bm{bm}_{prox}"] = {"zones": len(zs), "share_with_bm": round(with_bm / max(1, len(zs)), 3),
                                    "share_bm_is_bqa": round(bm_is_bqa / max(1, len(zs)), 3),
                                    "height_atr": q(h)}
    return out


def eq_gap_stats(bars):
    """Écart entre deux pivots hauts (resp. bas) consécutifs, en ATR."""
    atr = atr_series(bars)
    log = Engine(Config()).run(bars)
    gaps = []
    last = {}
    for e in log:
        if e.kind in ("PIVOT_HIGH", "PIVOT_LOW"):
            if e.kind in last:
                p = last[e.kind]
                gaps.append(abs(e.price - p.price) / atr[e.anchor_index])
            last[e.kind] = e
    return {"consecutive_same_side_gap_atr": q(gaps, (0.01, 0.02, 0.05, 0.1, 0.25, 0.5)),
            "share_below": {t: round(sum(1 for g in gaps if g <= t) / len(gaps), 4)
                            for t in (0.05, 0.1, 0.15, 0.25)}}


def main():
    res = {}
    for sym in ("EURUSD", "XAUUSD"):
        r = {}
        m15 = load(sym, "m15", "2015-01-01", "2022-01-01")
        h1 = load(sym, "h1", "2015-01-01", "2022-01-01")
        h4 = load(sym, "h4", "2015-01-01", "2022-01-01")
        d1 = load(sym, "d1", "2013-01-01", "2022-01-01")
        r["bars"] = {"m15": len(m15), "h1": len(h1), "h4": len(h4), "d1": len(d1)}
        r["body_ratio"] = {tf: body_ratio_stats(b) for tf, b in (("m15", m15), ("h1", h1), ("h4", h4))}
        r["atr14_pips"] = {tf: atr_in_pips(sym, b) for tf, b in (("m15", m15), ("h1", h1), ("h4", h4), ("d1", d1))}
        r["hour_profile_paris_m15"] = hour_profile(m15)
        sub = load(sym, "m15", "2019-01-01", "2021-01-01")
        r["pivots_m15"] = pivot_stats(sub)
        r["pivots_h4"] = pivot_stats(h4)
        r["pivots_d1"] = pivot_stats(d1)
        r["zones_m15_2019_2020"] = zone_stats(sub)
        r["eq_m15_2019_2020"] = eq_gap_stats(sub)
        res[sym] = r
        print(f"{sym} done", file=sys.stderr)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
