"""Matrice v2 pour la recherche d'asymétrie rentable (familles multiples, pas seulement SMV).

Une ligne = une opportunité (bougie i close, sens d), si au moins un déclencheur se produit :
  brk20 / brk96  : clôture au-delà du plus haut (bas) des 20 / 96 bougies précédentes -> suivre
  fail20         : mèche au-delà du plus haut (bas) des 20 bougies, clôture revenue dedans -> inverse
  mr5            : mouvement de 5 bougies >= 1,5 ATR -> retour à la moyenne (inverse)
  volx           : compression (amplitude des 20 bougies précédentes <= 4 ATR) puis bougie >= 1,5 ATR -> suivre
  pull           : tendance H1 (structure) d, et clôture sous le plus bas (sur le plus haut) des 10 bougies -> d
  sess           : bougie d'ouverture de Londres (8:00) ou de New York (9:30), heure locale -> deux sens
  zone / sweep / bos_follow / bos_fade : déclencheurs SMV (pour comparaison)

Entrée à l'OUVERTURE de la bougie i+1. Trois stops justifiés, risque borné à [0,25 ; 3] ATR :
  atr   : 1 ATR(14)
  swing : extrême des 10 dernières bougies (dont i) +/- 0,1 ATR
  sig   : extrême de la bougie de signal i +/- 0,1 ATR
Issues sur 96 bougies (24 h) pour TP = 1, 1,5, 2, 2,5, 3, 4 R : +k si TP d'abord ; -1 (ou pire si
gap au-delà du stop à l'ouverture d'une bougie) si stop d'abord ; même bougie = stop ; sinon
sortie à la clôture de la 96e bougie. Plus MFE avant stop, MAE, temps, coût en R.
Aucune issue n'est utilisée comme variable (colonnes « r_ », « mfe_ », « mae_ », « t_ »).

Usage : python research/asym/build_matrix2.py SYMBOL OUT.parquet [m15|h1|h4]
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
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

PARIS, LON, NY = ZoneInfo("Europe/Paris"), ZoneInfo("Europe/London"), ZoneInfo("America/New_York")
H = 96
TPS = (1.0, 1.5, 2.0, 2.5, 3.0, 4.0)
CAP = 999
RECENCY = ("BOS_CONTINUATION", "BOS_CHANGE", "LIQ_CLEAN", "LIQ_SIGNATURE", "FAIL", "IMBALANCE", "ZONE")


class Htf:
    def __init__(self, bars, minutes):
        if isinstance(minutes, list):          # bougies d'UT haute fournies directement
            self.bars = minutes
        else:
            origin = datetime(1970, 1, 5, tzinfo=timezone.utc) if minutes >= 10080 else None   # semaine : lundi
            self.bars = resample(bars, minutes, origin)
        self.eng = Engine(Config(enable_setups=False))
        self.k = 0
        self.closes = []

    def advance(self, t_close):
        while self.k < len(self.bars) and self.bars[self.k].t_close <= t_close:
            self.eng.on_bar(self.bars[self.k]); self.eng.log.clear()
            self.closes.append(self.bars[self.k].close)
            self.k += 1

    def feats(self, d):
        n = len(self.closes)
        if n < 21:
            return 0, np.nan, np.nan
        a = self.eng.ctx.atr[n - 1]
        s = self.eng.structure.trend
        trend = 0 if s == 0 else (1 if s == d else -1)
        mom5 = (self.closes[-1] - self.closes[-6]) * d / a if a > 0 else np.nan
        volr = a / np.mean(self.eng.ctx.atr[max(0, n - 50):n])
        return trend, mom5, volr


def first(mask):
    idx = np.flatnonzero(mask)
    return int(idx[0]) if idx.size else H + 1


def outcomes(row, prefix, E, risk, d, O, Hh, Ll, C, i, cost):
    hi, lo, op = Hh[i + 1:i + 1 + H], Ll[i + 1:i + 1 + H], O[i + 1:i + 1 + H]
    fav = ((hi - E) if d == 1 else (E - lo)) / risk
    adv = ((E - lo) if d == 1 else (hi - E)) / risk
    s = first(adv >= 1.0)
    if s <= H - 1:
        gap = ((E - op[s]) if d == 1 else (op[s] - E)) / risk if s > 0 else 0.0
        sl_r = -max(1.0, gap)
    for k in TPS:
        t = first(fav >= k)
        if t < s:
            r = k
        elif s <= H - 1:
            r = sl_r
        else:
            r = (C[i + H] - E) * d / risk
        row[f"r_{prefix}_{k:g}"] = r
    end = s if s <= H - 1 else H - 1
    row[f"mfe_{prefix}"] = float(fav[:end + 1].max())
    row[f"t_mfe_{prefix}"] = int(np.argmax(fav[:end + 1]))
    row[f"mae_{prefix}"] = float(adv.max())
    row[f"t_sl_{prefix}"] = s
    row[f"cost_{prefix}"] = cost / risk
    row[f"risk_atr_{prefix}"] = risk


HTF_OF = {"m15": (60, 240), "h1": (240, 1440), "h4": (1440, 10080)}


def build(symbol, tf="m15"):
    global H
    # horizon : 96 bougies (24 h en M15, 4 j en H1, 16 j en H4) ; D1 : 20 bougies (un mois)
    H = 20 if tf == "d1" else 96
    warm = 120 if tf == "d1" else 600
    bars = load(symbol, tf)
    n = len(bars)
    O = np.array([b.open for b in bars]); Hh = np.array([b.high for b in bars])
    Ll = np.array([b.low for b in bars]); C = np.array([b.close for b in bars])
    if tf == "d1":
        h1 = Htf(bars, 10080)                      # semaine agrégée depuis les D1
        h4 = Htf(bars, 10080)
    elif tf == "h4":
        # Les H4 du courtier sont alignées sur l'heure serveur : on prend les D1 du courtier, datées
        # 00:00-24:00 UTC (clôture déclarée après la clôture réelle, donc information retardée, jamais
        # avancée), et la semaine agrégée depuis ces D1.
        d1 = load(symbol, "d1")
        h1, h4 = Htf(bars, d1), Htf(d1, 10080)
    else:
        h1, h4 = (Htf(bars, m) for m in HTF_OF[tf])     # « h1 »/« h4 » = 1re et 2e UT supérieures
    eng = Engine(Config(zones_on="bos_origin"))
    last = {k: {1: -10**9, -1: -10**9} for k in RECENCY}
    zones, touched = {}, set()
    rows = []
    day_key, day_hi, day_lo, asia_hi, asia_lo = None, -np.inf, np.inf, -np.inf, np.inf
    atr_hist = []
    for b in bars:
        i = b.index
        h1.advance(b.t_close); h4.advance(b.t_close)
        evs = eng.on_bar(b); eng.log.clear()
        atr = eng.ctx.atr[i]; atr_hist.append(atr)
        loc = b.t_open.astimezone(PARIS)
        if loc.date() != day_key:
            day_key, day_hi, day_lo, asia_hi, asia_lo = loc.date(), -np.inf, np.inf, -np.inf, np.inf
        day_hi, day_lo = max(day_hi, b.high), min(day_lo, b.low)
        if loc.hour < 8:
            asia_hi, asia_lo = max(asia_hi, b.high), min(asia_lo, b.low)
        trig = {1: set(), -1: set()}
        zinfo = {1: None, -1: None}
        for e in evs:
            k = e.kind
            if k in last and e.direction in (1, -1):
                last[k][e.direction] = i
            if k == "ZONE":
                zones[e.ref] = (e, i)
            elif k == "ZONE_TOUCH" and e.data["zone"] not in touched:
                touched.add(e.data["zone"])
                z = zones.get(e.data["zone"])
                if z is not None:
                    trig[e.direction].add("zone")
                    zinfo[e.direction] = (3 if z[0].data["source"] == "BOS_CHANGE" else 2, i - z[1])
            elif k == "LIQ_CLEAN":
                trig[-e.direction].add("sweep")
            elif k in ("BOS_CONTINUATION", "BOS_CHANGE"):
                trig[e.direction].add("bos_follow"); trig[-e.direction].add("bos_fade")
        if i < warm or i + H + 1 >= n or atr <= 0:
            continue
        hi20, lo20 = Hh[i - 20:i].max(), Ll[i - 20:i].min()
        hi96, lo96 = Hh[i - 96:i].max(), Ll[i - 96:i].min()
        if C[i] > hi20: trig[1].add("brk20")
        if C[i] < lo20: trig[-1].add("brk20")
        if C[i] > hi96: trig[1].add("brk96")
        if C[i] < lo96: trig[-1].add("brk96")
        if Hh[i] > hi20 and C[i] <= hi20: trig[-1].add("fail20")
        if Ll[i] < lo20 and C[i] >= lo20: trig[1].add("fail20")
        m5 = (C[i] - C[i - 5]) / atr
        if m5 >= 1.5: trig[-1].add("mr5")
        if m5 <= -1.5: trig[1].add("mr5")
        comp_prev = (Hh[i - 20:i].max() - Ll[i - 20:i].min()) / atr
        if comp_prev <= 4.0 and (Hh[i] - Ll[i]) >= 1.5 * atr and C[i] != O[i]:
            trig[1 if C[i] > O[i] else -1].add("volx")
        st1 = h1.eng.structure.trend
        if st1 == 1 and C[i] < Ll[i - 10:i].min(): trig[1].add("pull")
        if st1 == -1 and C[i] > Hh[i - 10:i].max(): trig[-1].add("pull")
        sess = False
        for tz, hh, mm in ((LON, 8, 0), (NY, 9, 30)):
            dl = b.t_open.astimezone(tz)
            st_ = dl.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if b.t_open <= st_ < b.t_close:
                sess = True
        if sess:
            trig[1].add("sess"); trig[-1].add("sess")
        for d in (1, -1):
            if not trig[d]:
                continue
            row = {"i": i, "d": d, "year": loc.year, "t": b.t_close.timestamp(),
                   "hour": loc.hour, "dow": loc.weekday()}
            for f in ("brk20", "brk96", "fail20", "mr5", "volx", "pull", "sess", "zone", "sweep", "bos_follow", "bos_fade"):
                row["f_" + f] = int(f in trig[d])
            zi = zinfo[d]
            row["z_src"], row["z_age"] = (zi if zi else (np.nan, np.nan))
            # prix et volatilité (orientés selon d)
            row["mom1"] = (C[i] - C[i - 1]) * d / atr
            row["mom5"] = m5 * d
            row["mom20"] = (C[i] - C[i - 20]) * d / atr
            row["mom96"] = (C[i] - C[i - 96]) * d / atr
            seg = np.abs(np.diff(C[i - 50:i + 1]))
            row["er50"] = (C[i] - C[i - 50]) * d / seg.sum() if seg.sum() > 0 else 0.0
            row["comp20_prev"] = comp_prev
            row["range_atr"] = (Hh[i] - Ll[i]) / atr
            row["body_atr"] = (C[i] - O[i]) * d / atr
            row["wick_for_atr"] = ((Hh[i] - max(O[i], C[i])) if d == 1 else (min(O[i], C[i]) - Ll[i])) / atr
            row["wick_against_atr"] = ((min(O[i], C[i]) - Ll[i]) if d == 1 else (Hh[i] - max(O[i], C[i]))) / atr
            row["body_prev1"] = (C[i - 1] - O[i - 1]) * d / atr
            row["body_prev2"] = (C[i - 2] - O[i - 2]) * d / atr
            same = 0
            for j in range(i, i - 10, -1):
                if (C[j] - O[j]) * d > 0: same += 1
                else: break
            row["run_same"] = same
            row["atr_rel"] = atr / np.mean(atr_hist[max(0, i - 500):i])
            row["atr_trend"] = np.mean(atr_hist[i - 15:i + 1]) / np.mean(atr_hist[i - 96:i + 1])
            row["dist_hi20"] = ((hi20 - C[i]) if d == 1 else (C[i] - lo20)) / atr
            row["dist_lo20"] = ((C[i] - lo20) if d == 1 else (hi20 - C[i])) / atr
            row["dist_hi96"] = ((hi96 - C[i]) if d == 1 else (C[i] - lo96)) / atr
            row["dist_lo96"] = ((C[i] - lo96) if d == 1 else (hi96 - C[i])) / atr
            rng_ = day_hi - day_lo
            row["day_range_atr"] = rng_ / atr
            p = (C[i] - day_lo) / rng_ if rng_ > 0 else 0.5
            row["day_pos"] = p if d == 1 else 1 - p
            if np.isfinite(asia_hi) and loc.hour >= 8:
                row["asia_range_atr"] = (asia_hi - asia_lo) / atr
                row["asia_break"] = ((C[i] - asia_hi) if d == 1 else (asia_lo - C[i])) / atr
            else:
                row["asia_range_atr"], row["asia_break"] = np.nan, np.nan
            s = eng.structure
            row["ltf_trend"] = 0 if s.trend == 0 else (1 if s.trend == d else -1)
            row["h1_trend"], row["h1_mom5"], row["h1_volr"] = h1.feats(d)
            row["h4_trend"], row["h4_mom5"], row["h4_volr"] = h4.feats(d)
            for k in RECENCY:
                row[f"s_{k}_same"] = min(CAP, i - last[k][d]); row[f"s_{k}_opp"] = min(CAP, i - last[k][-d])
            lb = eng.liquidity
            hl = lb._heap_h[0][0] if lb._heap_h else np.nan
            ll = -lb._heap_l[0][0] if lb._heap_l else np.nan
            up, dn = (hl - C[i]) / atr, (C[i] - ll) / atr
            row["liq_target_atr"], row["liq_behind_atr"] = (up, dn) if d == 1 else (dn, up)
            row["atr"] = atr
            # issues (entrée à l'ouverture de i+1)
            E = O[i + 1]
            stops = {"atr": atr,
                     "swing": ((E - (Ll[i - 9:i + 1].min() - 0.1 * atr)) if d == 1 else ((Hh[i - 9:i + 1].max() + 0.1 * atr) - E)),
                     "sig": ((E - (Ll[i] - 0.1 * atr)) if d == 1 else ((Hh[i] + 0.1 * atr) - E))}
            for name, risk in stops.items():
                if 0.25 * atr <= risk <= 3.0 * atr:
                    outcomes(row, name, E, risk, d, O, Hh, Ll, C, i, COST[symbol])
                    row[f"risk_atr_{name}"] = risk / atr
            rows.append(row)
    df = pd.DataFrame(rows)
    df.insert(0, "symbol", symbol)
    return df


if __name__ == "__main__":
    df = build(sys.argv[1], sys.argv[3] if len(sys.argv) > 3 else "m15")
    for c in df.columns:
        if df[c].dtype == np.float64:
            df[c] = df[c].astype(np.float32)
    df.to_parquet(sys.argv[2])
    print(sys.argv[1], len(df))
