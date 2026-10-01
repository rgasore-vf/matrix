"""Jeu de données des setups pour le diagnostic et l'ajustement de la stratégie.

Chaque ligne = un setup NON rejeté, avec des caractéristiques connues à la clôture de la
bougie de création (aucune donnée future) et son issue (si déclenché).

Caractéristiques causales :
- type, label, sens, rr1 (cible 1 / risque), risk_atr ;
- tendance LTF au moment du setup (structure majeure M15) ;
- contexte H4 (bougies H4 agrégées depuis le M15, seulement closes) : tendance, position
  premium/discount de l'entrée dans la jambe H4 (protégé -> extrême), entrée dans une zone
  H4 active de même sens (« zone décisionnelle de l'UT supérieure », R-MTF-02, M1/7) ;
- heure de Paris et session, jour de la semaine.

Issue : r brut, r net de coûts, MFE, nombre de bougies avant déclenchement.
Usage : python research/setup_dataset.py SYMBOL [debut] [fin] > fichier.jsonl
"""
from __future__ import annotations

import json
import os
import sys
from datetime import timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from marketdata import load  # noqa: E402
from smv import Config, Engine  # noqa: E402
from smv.mtf import resample  # noqa: E402
from smv.types import BULL  # noqa: E402

PARIS = ZoneInfo("Europe/Paris")

# Coûts aller-retour en prix (HYPOTHÈSES de compte ECN : écart moyen + commission + glissement).
COST = {"EURUSD": 0.00010, "GBPUSD": 0.00012, "AUDUSD": 0.00012, "USDCAD": 0.00015,
        "USDCHF": 0.00015, "EURGBP": 0.00015, "EURCHF": 0.00020, "USDJPY": 0.012,
        "EURJPY": 0.015, "GBPJPY": 0.025, "AUDJPY": 0.020, "XAUUSD": 0.35}


def session(h: int) -> str:
    if 1 <= h < 8:
        return "asia"
    if 8 <= h < 13:
        return "london"
    if 13 <= h < 18:
        return "newyork"
    return "off"


def build(symbol: str, start: str | None = None, end: str | None = None, cfg: Config | None = None):
    cfg = cfg or Config()
    bars = load(symbol, "m15", start, end)
    htf_bars = resample(bars, 240)
    eng = Engine(cfg)
    htf = Engine(Config(enable_setups=False))
    hk = 0
    rows: dict[str, dict] = {}
    for b in bars:
        # alimenter l'UT haute avec les bougies H4 closes au plus tard à la clôture de b
        while hk < len(htf_bars) and htf_bars[hk].t_close <= b.t_close:
            htf.on_bar(htf_bars[hk])
            hk += 1
        for e in eng.on_bar(b):
            if e.kind == "SETUP" and e.data["rejected"] is None:
                d = e.direction
                entry = e.price
                st = htf.structure
                pd = None
                if st.trend != 0 and st.prot is not None and st.leg_ext is not None:
                    lo, hi = sorted((st.prot[0], st.leg_ext[0]))
                    if hi > lo:
                        pd = (entry - lo) / (hi - lo)       # 0 = bas de la jambe H4, 1 = haut
                in_zone = any(z.direction == d and z.bottom <= entry <= z.top for z in htf.zones._active)
                loc = b.t_close.astimezone(PARIS)
                rows[e.data["setup"]] = {
                    "symbol": symbol, "t": b.t_close.astimezone(timezone.utc).isoformat(),
                    "year": loc.year, "type": e.data["type"], "label": e.data["label"], "dir": d,
                    "rr1": e.data["rr"][0], "risk_atr": e.data["risk_atr"], "risk": e.data["risk"],
                    "ltf_trend": eng.structure.trend, "htf_trend": st.trend,
                    "htf_pd": None if pd is None else round(pd, 3),
                    "in_htf_zone": in_zone, "hour": loc.hour, "session": session(loc.hour),
                    "dow": loc.weekday(), "created": e.confirm_index, "status": "pending",
                }
            elif e.kind == "SETUP_TRIGGERED":
                rows[e.data["setup"]]["triggered"] = e.confirm_index
            elif e.kind == "SETUP_CLOSED":
                r = rows[e.data["setup"]]
                r["status"] = "closed"
                r["reason"] = e.data["reason"]
                r["r"] = e.data["r"]
                r["r_net"] = round(e.data["r"] - COST[symbol] / r["risk"], 4)
                r["mfe_r"] = e.data["mfe_r"]
                r["bars_in_trade"] = e.data["bars_in_trade"]
                r["closed"] = e.confirm_index
            elif e.kind == "SETUP_EXPIRED":
                rows[e.data["setup"]]["status"] = "expired:" + e.data["reason"]
    return list(rows.values())


if __name__ == "__main__":
    sym = sys.argv[1]
    a = sys.argv[2] if len(sys.argv) > 2 else None
    z = sys.argv[3] if len(sys.argv) > 3 else None
    for row in build(sym, a, z):
        print(json.dumps(row))
