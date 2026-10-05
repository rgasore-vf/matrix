"""Étude journée par journée (EURUSD) : toutes les entrées M15 dans le sens de la tendance H4.

But : voir OÙ et POURQUOI les entrées échouent, en particulier l'hypothèse « on entre à la fin du
mouvement ». Pas une stratégie : un instrument de diagnostic.

Signal (« suivre les 80 % ») : tendance H4 = d ; chaque BOS M15 (continuation ou changement) dans le
sens d crée une zone (bougie manipulatrice / bougie qui prend l'argent) ; ordre limite au bord
proximal, stop au bord distal, valable 16 h. Chaque signal est simulé indépendamment.
Issues : TP 2 R et 3 R, MFE avant stop (horizon 24 h). Conventions prudentes habituelles.

Contexte mesuré au REMPLISSAGE (causal) :
  h4_pos       position de l'entrée dans la jambe H4 : 0 = niveau protégé, 1 = extrême de la jambe
  h4_leg_atr   taille de la jambe H4 (protégé -> extrême) en ATR H4 : maturité du mouvement
  h4_bos_n     nombre de BOS de continuation H4 depuis le dernier BOS de changement H4
  m15_bos_n    rang du BOS M15 dans la tendance M15 (1 = premier BOS après le changement M15)
  room_zone_R  distance (en R) jusqu'à la zone H4 opposée la plus proche dans le sens du trade
  room_liq_R   distance (en R) jusqu'au premier niveau de liquidité H4 intact dans le sens du trade
  adr_used     amplitude du jour déjà parcourue / amplitude moyenne des 20 jours précédents
  hour, date   heure de Paris
Usage : python research/daystudy/build_day.py SYMBOLE ANNEE_DEBUT ANNEE_FIN SORTIE.parquet
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict
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
H, EXPIRY = 96, 64


def main(sym, y0, y1, out):
    bars = load(sym, "m15")
    h4 = load(sym, "h4") if sym == "XAUUSD" else resample(bars, 240)   # or : pause quotidienne, H4 du courtier
    heng = Engine(Config(zones_on="bos_origin", enable_setups=False))
    eng = Engine(Config(zones_on="bos_origin", enable_setups=False))
    cost = COST[sym]
    hk = 0
    h4_bos_n = 0
    m15_bos_n = 0
    pending = []                        # ordres en attente
    rows = []
    day_hi, day_lo, day_key = {}, {}, None
    ranges = []
    for b in bars:
        i = b.index
        while hk < len(h4) and h4[hk].t_close <= b.t_close:
            for e in heng.on_bar(h4[hk]):
                if e.kind == "BOS_CHANGE":
                    h4_bos_n = 0
                elif e.kind == "BOS_CONTINUATION":
                    h4_bos_n += 1
            heng.log.clear()
            hk += 1
        evs = eng.on_bar(b)
        eng.log.clear()
        loc = b.t_open.astimezone(PARIS)
        if loc.date() != day_key:
            if day_key is not None:
                ranges.append(day_hi[day_key] - day_lo[day_key])
            day_key = loc.date()
            day_hi[day_key], day_lo[day_key] = b.high, b.low
        day_hi[day_key] = max(day_hi[day_key], b.high)
        day_lo[day_key] = min(day_lo[day_key], b.low)
        for e in evs:
            if e.kind == "BOS_CHANGE":
                m15_bos_n = 1
            elif e.kind == "BOS_CONTINUATION":
                m15_bos_n += 1
        if loc.year < y0 or loc.year > y1 or i < 2000:
            continue
        s = heng.structure
        d = s.trend
        # --- remplissages / annulations
        still = []
        for o in pending:
            dd, E, S = o["d"], o["E"], o["S"]
            filled = (b.low <= E) if dd == 1 else (b.high >= E)
            if filled:
                rows.append(fill(o, bars, i, heng, ranges, day_hi[day_key] - day_lo[day_key], loc, cost))
            elif ((b.close < S) if dd == 1 else (b.close > S)) or i > o["deadline"]:
                pass
            else:
                still.append(o)
        pending = still
        # --- nouveaux signaux : BOS M15 dans le sens de la tendance H4
        if d == 0:
            continue
        for e in evs:
            if e.kind in ("BOS_CHANGE", "BOS_CONTINUATION") and e.direction == d:
                z = next((x for x in evs if x.kind == "ZONE" and x.direction == d
                          and x.data.get("source") == e.kind), None)
                if z is None:
                    continue
                E, S = z.data["proximal"], z.data["distal"]
                if (E - S) * d <= 0:
                    continue
                pending.append({"d": d, "E": E, "S": S, "sig_i": i, "deadline": i + EXPIRY,
                                "kind": e.kind, "m15_bos_n": m15_bos_n, "h4_bos_n": h4_bos_n,
                                "sig_t": b.t_open.timestamp()})
    df = pd.DataFrame(rows)
    df.insert(0, "symbol", sym)
    df.to_parquet(out)
    print(sym, len(df))


def fill(o, bars, f, heng, ranges, day_rng, loc, cost):
    d, E, S = o["d"], o["E"], o["S"]
    risk = abs(E - S)
    s = heng.structure
    atr4 = heng.ctx.atr[-1]
    prot = s.prot[0] if s.prot else None
    ext = s.leg_ext[0] if s.leg_ext else None
    h4_pos = (E - prot) / (ext - prot) if prot is not None and ext is not None and ext != prot else np.nan
    leg = abs(ext - prot) / atr4 if prot is not None and ext is not None else np.nan
    opp = [z for z in heng.zones._active if z.direction == -d and z.source != "BREAKER"
           and ((z.proximal > E) if d == 1 else (z.proximal < E))]
    room_zone = min((abs(z.proximal - E) for z in opp), default=np.nan) / risk
    liq = heng.liquidity.intact_targets(E, d)
    room_liq = abs(liq[0].price - E) / risk if liq else np.nan
    adr = np.mean(ranges[-20:]) if len(ranges) >= 5 else np.nan
    # simulation
    mfe, end_r, hit2, hit3, stop = 0.0, None, False, False, False
    n = len(bars)
    for j in range(f, min(n, f + H + 1)):
        b = bars[j]
        if (b.low <= S) if d == 1 else (b.high >= S):
            end_r, stop = -1.0, True
            break
        if j > f:
            fav = ((b.high - E) if d == 1 else (E - b.low)) / risk
            mfe = max(mfe, fav)
            hit2 = hit2 or fav >= 2
            hit3 = hit3 or fav >= 3
    if end_r is None:
        end_r = (bars[min(n - 1, f + H)].close - E) * d / risk
    exit_bar = j
    return {"date": loc.date().isoformat(), "hour": loc.hour, "fill_i": f, "sig_i": o["sig_i"],
            "fill_t": bars[f].t_open.timestamp(), "exit_i": exit_bar, "d": d, "E": E, "S": S,
            "kind": o["kind"], "risk_pips": risk / 0.0001, "cost_R": cost / risk,
            "h4_pos": h4_pos, "h4_leg_atr": leg, "h4_bos_n": o["h4_bos_n"], "m15_bos_n": o["m15_bos_n"],
            "room_zone_R": room_zone, "room_liq_R": room_liq,
            "adr_used": day_rng / adr if adr and adr > 0 else np.nan,
            "mfe_R": mfe, "stopped": int(stop),
            "r2": 2.0 if hit2 else end_r, "r3": 3.0 if hit3 else end_r}


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
