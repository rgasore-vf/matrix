"""Méthode combinée des modules 1 à 5 : zone de décision en grande UT, entrée en petite UT.

Lecture des transcriptions (docs/TOPDOWN_RESEARCH.md §1) traduite en règles, version v1 :

  HTF (H4 ou H1, agrégé depuis le M15, bougies closes uniquement)
    1. biais = tendance de la structure majeure HTF (module 1) ;
    2. zone de décision = zone HTF ACTIVE, « décisionnelle » (origine d'un BOS de changement),
       dans le sens du biais (modules 2-3).
  LTF (M15)
    3. armement : une bougie M15 touche la zone HTF (bord proximal) ;
    4. cause (module 4) pendant l'armement : BOS de changement de tendance M15 dans le sens du trade
       (« intention »). Le FAIL et la prise de liquidité (LIQ_CLEAN d'un niveau opposé) sont
       ENREGISTRÉS (has_fail, has_sweep, strict = fail puis prise) et non imposés : la séquence
       stricte ne donnait que 11 trades en 9 ans sur EURUSD (le moteur n'émet qu'un FAIL par jambe) ;
    5. entrée : ordre limite sur le bord proximal de la zone M15 créée par ce BOS ;
       stop sur le bord distal (mèche de la bougie qui prend l'argent) (modules 2-3, 5).
  Sortie : AUCUNE cible imposée. On mesure ce que le prix donne :
    MFE en R avant le stop, R obtenu pour des TP fixes 1 à 5 R, R au premier niveau intact
    M15 et au premier niveau intact HTF (module 4 : intact buyer/seller).

Conventions prudentes : le prix doit toucher l'entrée pour qu'elle soit remplie ; sur la bougie de
remplissage seul le stop est évalué ; stop et cible dans la même bougie = stop ; gap au-delà du stop
compté à l'ouverture ; horizon 96 bougies M15 (24 h) après le remplissage, sortie à la clôture.
Un seul trade à la fois par instrument. Ordre annulé après 64 bougies (16 h) ou si la zone M15 casse
(clôture au-delà du stop). v1.0 annulait aussi l'ordre si le prix atteignait +1 R avant l'entrée :
au BOS le prix est presque toujours déjà au-delà, 85 % des ordres étaient annulés à tort.

Usage : python research/topdown/build_td.py SYMBOLE {240|60} SORTIE.parquet
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
H = 96            # horizon après remplissage (bougies M15)
EXPIRY = 64       # durée de vie de l'ordre limite (16 h)
ARM = 64          # durée de l'armement après la touche de la zone HTF (16 h)
PIP = {"XAUUSD": 0.1, "USDJPY": 0.01, "EURJPY": 0.01, "GBPJPY": 0.01, "AUDJPY": 0.01}
TPS = (1, 1.5, 2, 3, 4, 5)
MFE_K = (1, 2, 3, 4, 5, 6, 8, 10)


class Htf:
    def __init__(self, bars, minutes):
        self.bars = resample(bars, minutes)
        self.eng = Engine(Config(zones_on="bos_origin", enable_setups=False))
        self.k = 0

    def advance(self, t_close):
        while self.k < len(self.bars) and self.bars[self.k].t_close <= t_close:
            self.eng.on_bar(self.bars[self.k])
            self.eng.log.clear()
            self.k += 1

    def zones(self, d):
        if self.eng.structure.trend != d:
            return []
        return [z for z in self.eng.zones._active
                if z.direction == d and z.decisional and z.source != "BREAKER" and z.status == "ACTIVE"]


def simulate(bars, f, d, E, S, targets, cost):
    """Trade rempli à la bougie f. Renvoie le dictionnaire des issues."""
    risk = abs(E - S)
    n = len(bars)
    out = {"risk": risk, "cost_R": cost / risk}
    tp_px = {k: E + d * k * risk for k in TPS}
    tg = {f"tgt{j}": (t, abs(t - E) / risk) for j, t in targets.items() if t is not None}
    hit = {}
    mfe, end_r, exit_i, stopped = 0.0, None, None, False
    for j in range(f, min(n, f + H + 1)):
        b = bars[j]
        fav = ((b.high - E) if d == 1 else (E - b.low)) / risk
        adv_hit = (b.low <= S) if d == 1 else (b.high >= S)
        if adv_hit:
            gap = ((S - b.open) if d == 1 else (b.open - S)) / risk if j > f else 0.0
            end_r = -1.0 - max(0.0, gap)
            exit_i, stopped = j, True
            break
        if j > f:
            mfe = max(mfe, fav)
            for k, p in tp_px.items():
                if k not in hit and ((b.high >= p) if d == 1 else (b.low <= p)):
                    hit[k] = j
            for name, (p, _) in tg.items():
                if name not in hit and ((b.high >= p) if d == 1 else (b.low <= p)):
                    hit[name] = j
    if not stopped:
        j = min(n - 1, f + H)
        end_r = (bars[j].close - E) * d / risk
        exit_i = j
    out["mfe_R"] = mfe
    out["end_R"] = end_r                  # sans cible : stop ou clôture à l'horizon
    out["stopped"] = int(stopped)
    out["bars_to_exit"] = exit_i - f
    for k in TPS:
        out[f"r_tp{k:g}"] = float(k) if k in hit else end_r
        out[f"t_tp{k:g}"] = (hit[k] - f) if k in hit else -1
    for name, (p, dist) in tg.items():
        out[f"{name}_R"] = dist
        out[f"r_{name}"] = dist if name in hit else end_r
    for k in MFE_K:
        out[f"mfe_ge{k}"] = int(mfe >= k)
    return out


def build(symbol, htf_min):
    bars = load(symbol, "m15")
    n = len(bars)
    htf = Htf(bars, htf_min)
    eng = Engine(Config(zones_on="bos_origin", enable_setups=False))
    cost = COST[symbol]
    state = {1: None, -1: None}           # séquence en cours par sens
    order = None                          # ordre limite en attente
    busy_until = -1                       # un trade à la fois
    rows = []
    from collections import Counter
    fun = Counter()
    for b in bars:
        i = b.index
        htf.advance(b.t_close)
        evs = eng.on_bar(b)
        eng.log.clear()
        if i < 500:
            continue
        atr = eng.ctx.atr[i]
        # --- ordre en attente : remplissage, annulation
        if order is not None:
            d, E, S = order["d"], order["E"], order["S"]
            filled = (b.low <= E) if d == 1 else (b.high >= E)
            tp1 = E + d * abs(E - S)
            ran_away = False   # v1.1 : pas d'annulation sur fuite du prix (le cours attend le retracement)
            broke = (b.close < S) if d == 1 else (b.close > S)
            if filled:
                res = simulate(bars, i, d, E, S, order["targets"], cost)
                loc = b.t_open.astimezone(PARIS)
                rows.append({**order["meta"], "fill_i": i, "fill_t": b.t_open.timestamp(),
                             "year": loc.year, "hour": loc.hour, "dow": loc.weekday(),
                             "date": loc.date().isoformat(), "wait_bars": i - order["meta"]["sig_i"],
                             **res})
                busy_until = i + res["bars_to_exit"]
                order = None
                fun["filled"] += 1
            elif ran_away or broke or i > order["deadline"]:
                fun["cancel_runaway" if ran_away else "cancel_broken" if broke else "cancel_expired"] += 1
                order = None
        # --- séquences : armement par touche de zone HTF
        for d in (1, -1):
            st = state[d]
            if st is not None and (i > st["deadline"] or not any(z.zid == st["zid"] for z in htf.zones(d))):
                state[d] = st = None
            if st is None:
                for z in htf.zones(d):
                    touched = (b.low <= z.proximal and b.close >= z.distal) if d == 1 else \
                              (b.high >= z.proximal and b.close <= z.distal)
                    if touched:
                        fun["armed"] += 1
                        state[d] = {"zid": z.zid, "armed": i, "deadline": i + ARM,
                                    "fail": None, "sweep": None, "hz": (z.proximal, z.distal)}
                        break
                continue
            for e in evs:
                k = e.kind
                if k == "FAIL" and e.direction == d and st["fail"] is None:
                    st["fail"] = i
                elif k == "LIQ_CLEAN" and e.direction == -d and st["sweep"] is None:
                    st["sweep"] = i
                elif k == "BOS_CHANGE" and e.direction == d:
                    fun["bosc_in_arm"] += 1
                    z = next((x for x in evs if x.kind == "ZONE" and x.direction == d
                              and x.data.get("source") == "BOS_CHANGE"), None)
                    if z is None:
                        fun["no_zone"] += 1
                    elif order is not None or i <= busy_until:
                        fun["busy"] += 1
                    if z is not None and order is None and i > busy_until:
                        E, S = z.data["proximal"], z.data["distal"]
                        if (E - S) * d > 0:
                            fun["order_created"] += 1
                            lt = eng.liquidity.intact_targets(E, d)
                            ht = htf.eng.liquidity.intact_targets(E, d)
                            f_, s_ = st["fail"], st["sweep"]
                            order = {"d": d, "E": E, "S": S, "deadline": i + EXPIRY,
                                     "targets": {"1": lt[0].price if lt else None,
                                                 "2": lt[1].price if len(lt) > 1 else None,
                                                 "H": ht[0].price if ht else None},
                                     "meta": {"sig_i": i, "d": d, "E": E, "S": S, "atr": atr,
                                              "risk_atr": abs(E - S) / atr,
                                              "risk_pips": abs(E - S) / PIP.get(symbol, 0.0001),
                                              "armed_i": st["armed"],
                                              "has_fail": int(f_ is not None), "has_sweep": int(s_ is not None),
                                              "strict": int(f_ is not None and s_ is not None and f_ <= s_),
                                              "htf_zone": st["zid"],
                                              "zone_doji": int(bool(z.data.get("doji_signature"))),
                                              "zone_bm": int(z.data.get("bm_index") is not None)}}
                    state[d] = None
                    break
    print(symbol, htf_min, dict(fun), file=sys.stderr)
    df = pd.DataFrame(rows)
    df.insert(0, "symbol", symbol)
    df.insert(1, "htf", htf_min)
    return df


if __name__ == "__main__":
    sym, htf_min, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    df = build(sym, htf_min)
    df.to_parquet(out)
    print(sym, htf_min, len(df))
