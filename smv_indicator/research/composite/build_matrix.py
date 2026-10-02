"""Matrice événementielle pour la recherche de stratégies composites.

Une ligne = une opportunité (bougie i close, sens d). Une opportunité existe si au moins un
déclencheur se produit à la clôture de i :
  - première touche d'une zone de sens d (retour sur zone) ;
  - prise en mèche d'une liquidité opposée (pour un achat : un bas pris sans clôture dessous) ;
  - BOS (continuation ou changement) de sens -d (BOS lu à l'envers, contrarien) ;
  - prise d'une borne de consolidation de sens -d (STB/spring pour un achat...) ;
  - prise du niveau protégé contre la tendance d.

Toutes les caractéristiques sont connues à la clôture de i (moteur causal, UT hautes closes).
Les issues futures sont dans des colonnes préfixées « y_ » et ne servent jamais de variables.

Usage : python research/composite/build_matrix.py SYMBOL OUT.parquet
"""
from __future__ import annotations

import os
import sys
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", ".."))

from marketdata import load  # noqa: E402
from setup_dataset import COST  # noqa: E402
from smv import Config, Engine  # noqa: E402
from smv.mtf import resample  # noqa: E402

PARIS = ZoneInfo("Europe/Paris")
CAP = 999                     # « jamais vu récemment »
HORIZON = 200                 # bougies pour les courses
TP_LEVELS = (0.5, 1.0, 1.5, 2.0)
SL_LEVELS = (0.5, 1.0, 2.0)
GEOMETRIES = ((1.0, 1.0), (1.5, 1.0), (2.0, 1.0), (1.0, 0.5), (0.5, 1.0), (2.0, 2.0))

# Événements dont on mémorise la dernière occurrence par sens (sens = direction de l'événement).
RECENCY_KINDS = ("BOS_CONTINUATION", "BOS_CHANGE", "LIQ_CLEAN", "LIQ_BOS", "LIQ_SIGNATURE",
                 "FAIL", "IMBALANCE", "PROTECTED_SWEEP", "EQUAL_LEVELS", "BREAKER",
                 "ZONE", "RANGE_EXIT", "CAUSE_COMPLETE")
RANGE_LABELS = ("STB", "SPRING", "UT", "UTAD", "UA", "MSO")


class Htf:
    """Moteur d'UT haute alimenté uniquement par des bougies closes."""

    def __init__(self, bars, minutes):
        self.bars = resample(bars, minutes)
        self.eng = Engine(Config(enable_setups=False))
        self.k = 0

    def advance(self, t_close):
        while self.k < len(self.bars) and self.bars[self.k].t_close <= t_close:
            self.eng.on_bar(self.bars[self.k])
            self.eng.log.clear()
            self.k += 1

    def features(self, price, d):
        s = self.eng.structure
        trend = 0 if s.trend == 0 else (1 if s.trend == d else -1)
        pd_ = np.nan
        if s.trend != 0 and s.prot is not None and s.leg_ext is not None:
            lo, hi = sorted((s.prot[0], s.leg_ext[0]))
            if hi > lo:
                p = (price - lo) / (hi - lo)
                pd_ = p if d == 1 else 1 - p          # 0 = discount pour l'achat, premium pour la vente
        in_zone = any(z.direction == d and z.bottom <= price <= z.top for z in self.eng.zones._active)
        return trend, pd_, in_zone


def first_hit(path, level):
    idx = np.flatnonzero(path >= level)
    return idx[0] if idx.size else HORIZON + 1


def build(symbol: str) -> pd.DataFrame:
    bars = load(symbol, "m15")
    n = len(bars)
    H = np.array([b.high for b in bars]); L = np.array([b.low for b in bars]); C = np.array([b.close for b in bars])
    h1, h4 = Htf(bars, 60), Htf(bars, 240)
    eng = Engine(Config(zones_on="all_pivots", enable_imbalance=True))
    last = {k: {1: -10**9, -1: -10**9} for k in RECENCY_KINDS + tuple("RS_" + x for x in RANGE_LABELS)}
    zones = {}
    touched = set()
    rows = []
    atr_hist = []
    for b in bars:
        i = b.index
        h1.advance(b.t_close); h4.advance(b.t_close)
        evs = eng.on_bar(b)
        eng.log.clear()
        atr = eng.ctx.atr[i]
        atr_hist.append(atr)
        triggers = {1: {}, -1: {}}
        for e in evs:
            k = e.kind
            if k in last and e.direction in (1, -1):
                last[k][e.direction] = i
            if k == "ZONE" or k == "BREAKER":
                zones[e.ref] = (e, i)
            if k == "ZONE_TOUCH" and e.data["zone"] not in touched:
                touched.add(e.data["zone"])
                z = zones.get(e.data["zone"])
                if z is not None:
                    ze, zi = z
                    src = {"BOS_CHANGE": 3, "BOS_CONTINUATION": 2, "PIVOT": 1, "BREAKER": 0}.get(ze.data["source"], 0)
                    prev = triggers[e.direction].get("zone")
                    if prev is None or src > prev["src"]:
                        hgt = abs(ze.data["proximal"] - ze.data["distal"])
                        pen = (ze.data["proximal"] - b.close) * e.direction / hgt if hgt > 0 else np.nan
                        triggers[e.direction]["zone"] = {
                            "src": src, "bm": int(ze.data["bm_index"] is not None),
                            "doji": int(ze.data["doji_signature"]), "h_atr": hgt / atr,
                            "age": i - zi, "pen": pen,
                            "dist_atr": (b.close - ze.data["distal"]) * e.direction / atr}
            elif k == "LIQ_CLEAN":
                triggers[-e.direction]["sweep"] = 1
            elif k in ("BOS_CONTINUATION", "BOS_CHANGE"):
                triggers[-e.direction]["bos"] = 2 if k == "BOS_CHANGE" else 1
                triggers[-e.direction]["bos_amp"] = (b.close - e.price) * e.direction / atr
            elif k == "RANGE_SWEEP":
                lab = e.data["label_candidate"].split("+")[0]
                last["RS_" + lab][e.direction] = i
                triggers[-e.direction]["rsweep"] = RANGE_LABELS.index(lab) + 1
            elif k == "PROTECTED_SWEEP":
                triggers[-e.direction]["psweep"] = 1
        if i < 600 or i + 2 >= n:
            continue
        for d in (1, -1):
            t = triggers[d]
            if not t:
                continue
            row = {"i": i, "d": d}
            z = t.get("zone")
            row["trg_zone"] = int(z is not None)
            for key in ("src", "bm", "doji", "h_atr", "age", "pen", "dist_atr"):
                row["z_" + key] = z[key] if z else np.nan
            row["trg_sweep"] = t.get("sweep", 0)
            row["trg_bos"] = t.get("bos", 0)
            row["bos_amp"] = t.get("bos_amp", np.nan)
            row["trg_rsweep"] = t.get("rsweep", 0)
            row["trg_psweep"] = t.get("psweep", 0)
            for k in last:
                row["s_" + k + "_same"] = min(CAP, i - last[k][d])
                row["s_" + k + "_opp"] = min(CAP, i - last[k][-d])
            # structure M15
            s = eng.structure
            row["ltf_trend"] = 0 if s.trend == 0 else (1 if s.trend == d else -1)
            lpd = np.nan
            if s.trend != 0 and s.prot is not None and s.leg_ext is not None:
                lo, hi = sorted((s.prot[0], s.leg_ext[0]))
                if hi > lo:
                    p = (b.close - lo) / (hi - lo)
                    lpd = p if d == 1 else 1 - p
            row["ltf_pd"] = lpd
            row["h1_trend"], row["h1_pd"], row["h1_zone"] = h1.features(b.close, d)
            row["h4_trend"], row["h4_pd"], row["h4_zone"] = h4.features(b.close, d)
            # liquidité intacte la plus proche (cible côté d, risque côté -d)
            lb = eng.liquidity
            hi_lv = lb._heap_h[0][0] if lb._heap_h else np.nan
            lo_lv = -lb._heap_l[0][0] if lb._heap_l else np.nan
            up, dn = (hi_lv - b.close) / atr, (b.close - lo_lv) / atr
            row["liq_target_atr"] = up if d == 1 else dn
            row["liq_behind_atr"] = dn if d == 1 else up
            # régime
            row["atr_rel"] = atr / np.mean(atr_hist[i - 500:i])
            row["mom5"] = (C[i] - C[i - 5]) * d / atr
            row["mom20"] = (C[i] - C[i - 20]) * d / atr
            row["mom96"] = (C[i] - C[i - 96]) * d / atr
            seg = np.abs(np.diff(C[i - 50:i + 1]))
            row["er50"] = (C[i] - C[i - 50]) * d / seg.sum() if seg.sum() > 0 else 0.0
            row["compress20"] = (H[i - 19:i + 1].max() - L[i - 19:i + 1].min()) / atr
            hh, ll = H[i - 95:i + 1].max(), L[i - 95:i + 1].min()
            pos = (C[i] - ll) / (hh - ll) if hh > ll else 0.5
            row["daypos"] = pos if d == 1 else 1 - pos
            row["body_atr"] = (b.close - b.open) * d / atr
            row["wick_against_atr"] = ((min(b.open, b.close) - b.low) if d == 1 else (b.high - max(b.open, b.close))) / atr
            r = eng.ranges.current
            row["in_range"] = int(r is not None and not r.closed)
            row["range_age"] = (i - r.open_index) if (r is not None and not r.closed) else np.nan
            loc = b.t_close.astimezone(PARIS)
            row["hour"] = loc.hour; row["dow"] = loc.weekday(); row["year"] = loc.year
            row["t"] = b.t_close.timestamp()
            row["atr"] = atr
            row["cost_atr"] = COST[symbol] / atr
            # issues futures (jamais utilisées comme variables)
            e0 = C[i]
            j1 = min(n, i + 1 + HORIZON)
            fav = ((H[i + 1:j1] - e0) if d == 1 else (e0 - L[i + 1:j1])) / atr
            adv = ((e0 - L[i + 1:j1]) if d == 1 else (H[i + 1:j1] - e0)) / atr
            if len(fav) < HORIZON:
                continue
            ft = {tp: first_hit(fav, tp) for tp in TP_LEVELS}
            st = {sl: first_hit(adv, sl) for sl in SL_LEVELS}
            for tp, sl in GEOMETRIES:
                a, c = ft[tp], st[sl]
                if a > HORIZON and c > HORIZON:
                    row[f"y_{tp}_{sl}"] = np.nan
                else:
                    row[f"y_{tp}_{sl}"] = 1.0 if a < c else 0.0    # même bougie = perte (prudent)
                row[f"t_{tp}_{sl}"] = min(a, c)
            row["y_mfe48"] = fav[:48].max(); row["y_mae48"] = adv[:48].max()
            rows.append(row)
    df = pd.DataFrame(rows)
    df.insert(0, "symbol", symbol)
    return df


if __name__ == "__main__":
    df = build(sys.argv[1])
    for c in df.columns:
        if df[c].dtype == np.float64:
            df[c] = df[c].astype(np.float32)
    df.to_parquet(sys.argv[2])
    print(sys.argv[1], len(df))
