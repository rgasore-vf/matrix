"""XAUUSD : dans quels contextes la tendance H4 tient-elle à l'échelle de quelques heures ?

Une ligne toutes les 2 bougies M15 (30 min) quand la structure H4 a une tendance d.
Issue : course ±x ATR H4 (x = 0,5 et 1), dans les 96 bougies M15 (24 h) ; 1 si +x dans le sens d
est atteint d'abord, 0 si -x d'abord, vide si aucun des deux ou les deux dans la même bougie.
Toutes les variables sont connues à la clôture de la bougie (bougies H4 et D1 closes uniquement).
H4 et D1 = bougies du courtier (l'agrégation UTC depuis le M15 perdait une bougie H4 par jour et toutes les
D1 sur l'or, à cause de la pause quotidienne).

Variables :
  pos4        position dans la jambe H4 (0 = niveau protégé, 1 = extrême)
  leg4_atr    taille de la jambe H4 en ATR H4
  age4        bougies H4 depuis le dernier BOS H4 ; nbos4 : BOS de continuation depuis le changement
  last4       type du dernier BOS H4 (1 = changement, 0 = continuation)
  d1_agree    tendance D1 : 1 même sens, -1 sens opposé, 0 sans tendance
  m15_agree   tendance M15 dans le sens d (1/-1/0) ; m15_age : bougies M15 depuis le dernier BOS M15
  in_zone4    le prix est dans une zone H4 active de sens d (demande pour un achat) ; zone_age4
  touched4    une zone H4 de sens d a été touchée dans les 8 dernières bougies H4 sans casser
  opp_zone_atr distance à la zone H4 opposée la plus proche dans le sens d, en ATR H4
  prot_atr    distance au niveau protégé H4 (invalidation), en ATR H4
  volr4       ATR H4 / moyenne des 100 dernières ATR H4
  mom4        variation des 6 dernières bougies H4 dans le sens d, en ATR H4
  day_used    amplitude du jour / moyenne des 20 jours ; hour, dow (Paris)
Usage : python research/xau/build_ctx.py SORTIE.parquet [SYMBOLE]
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
from smv import Config, Engine  # noqa: E402
from smv.mtf import resample  # noqa: E402

PARIS = ZoneInfo("Europe/Paris")
STEP = int(os.environ.get("CTX_STEP", "2"))   # 2 = recherche ; 1 = chaque bougie, comme l EA


class Tf:
    def __init__(self, bars):
        self.bars = bars                  # bougies du courtier (H4 : heure serveur convertie ; D1 : clôture déclarée à 24 h, information retardée)
        self.eng = Engine(Config(zones_on="bos_origin", enable_setups=False))
        self.k = 0
        self.last_bos, self.nbos, self.last_kind = -999, 0, 0
        self.touch_k = {}

    def advance(self, t_close):
        while self.k < len(self.bars) and self.bars[self.k].t_close <= t_close:
            for e in self.eng.on_bar(self.bars[self.k]):
                if e.kind == "BOS_CHANGE":
                    self.last_bos, self.nbos, self.last_kind = self.k, 0, 1
                elif e.kind == "BOS_CONTINUATION":
                    self.last_bos, self.nbos, self.last_kind = self.k, self.nbos + 1, 0
                elif e.kind == "ZONE_TOUCH":
                    self.touch_k[e.direction] = self.k
            self.eng.log.clear()
            self.k += 1


def race(H, L, i, up, dn, d, hz=96):
    for j in range(i + 1, min(len(H), i + 1 + hz)):
        hu = H[j] >= up if d == 1 else L[j] <= up
        hd = L[j] <= dn if d == 1 else H[j] >= dn
        if hu and hd:
            return np.nan
        if hu:
            return 1.0
        if hd:
            return 0.0
    return np.nan


def main(out, sym="XAUUSD"):
    bars = load(sym, "m15")
    h4, d1 = Tf(load(sym, "h4")), Tf(load(sym, "d1"))
    eng = Engine(Config(zones_on="bos_origin", enable_setups=False))
    H = np.array([b.high for b in bars]); L = np.array([b.low for b in bars]); C = np.array([b.close for b in bars])
    m15_last = -999
    day_key, dhi, dlo, ranges = None, 0.0, 0.0, []
    rows = []
    for b in bars:
        i = b.index
        h4.advance(b.t_close); d1.advance(b.t_close)
        for e in eng.on_bar(b):
            if e.kind in ("BOS_CHANGE", "BOS_CONTINUATION"):
                m15_last = i
        eng.log.clear()
        loc = b.t_open.astimezone(PARIS)
        if loc.date() != day_key:
            if day_key is not None:
                ranges.append(dhi - dlo)
            day_key, dhi, dlo = loc.date(), b.high, b.low
        dhi, dlo = max(dhi, b.high), min(dlo, b.low)
        if i < 4000 or i % STEP or h4.k < 120:
            continue
        s = h4.eng.structure
        d = s.trend
        if d == 0 or s.prot is None or s.leg_ext is None:
            continue
        atr4 = h4.eng.ctx.atr[-1]
        if atr4 <= 0:
            continue
        hist = h4.eng.ctx.atr[-100:]
        prot, ext = s.prot[0], s.leg_ext[0]
        zones = [z for z in h4.eng.zones._active if z.direction == d and z.source != "BREAKER"]
        in_zone = [z for z in zones if z.bottom <= C[i] <= z.top]
        opp = [z for z in h4.eng.zones._active if z.direction == -d and z.source != "BREAKER"
               and ((z.proximal - C[i]) * d > 0)]
        k6 = max(0, h4.k - 7)
        mom = (h4.bars[h4.k - 1].close - h4.bars[k6].close) * d / atr4
        t4 = h4.touch_k.get(d, -999)
        row = {"i": i, "year": loc.year, "hour": loc.hour, "dow": loc.weekday(), "d": d,
               "pos4": (C[i] - prot) / (ext - prot) if ext != prot else np.nan,
               "leg4_atr": abs(ext - prot) / atr4, "age4": h4.k - 1 - h4.last_bos, "nbos4": h4.nbos,
               "last4": h4.last_kind, "d1_agree": int(np.sign(d1.eng.structure.trend * d)),
               "m15_agree": int(np.sign(eng.structure.trend * d)), "m15_age": i - m15_last,
               "in_zone4": int(bool(in_zone)), "touched4": int(h4.k - 1 - t4 <= 8),
               "opp_zone_atr": min((abs(z.proximal - C[i]) for z in opp), default=np.nan) / atr4,
               "prot_atr": abs(C[i] - prot) / atr4, "volr4": atr4 / np.mean(hist), "mom4": mom,
               "day_used": (dhi - dlo) / np.mean(ranges[-20:]) if len(ranges) >= 5 else np.nan}
        for x in (0.5, 1.0):
            row[f"r{x:g}"] = race(H, L, i, C[i] + d * x * atr4, C[i] - d * x * atr4, d)
        rows.append(row)
    pd.DataFrame(rows).to_parquet(out)
    print(sym, len(rows))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "XAUUSD")
