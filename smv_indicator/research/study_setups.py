"""Backtest des setups (golden entry, concept entry) sur données réelles et sur séries mélangées.

Question : les setups produits par le moteur, avec la politique de sortie décrite dans
smv/setups.py (entrée limite au bord proximal, stop au bord distal, sortie totale sur la
première liquidité intacte), ont-ils une espérance positive après coûts, et font-ils mieux
que le hasard ?

Deux références :
1. le modèle de la ruine du joueur : sur une marche aléatoire sans dérive, une course entre une
   cible à distance k et un stop à distance h est gagnée avec la probabilité h / (h + k) ; un
   setup ne vaut donc quelque chose que si son taux de réussite dépasse 1 / (1 + RR) ;
2. les séries mélangées (study_nulls.shuffled) : mêmes bougies, ordre aléatoire.

Coûts (HYPOTHÈSES, à remplacer par ceux du courtier) : EURUSD 1,0 pip aller-retour
(écart ~0,2 pip + commission ~0,7 pip sur compte ECN, plus glissement), XAUUSD 0,35 $.
Ils sont convertis en R pour chaque trade : r_net = r - coût / risque.

Usage : python research/study_setups.py SYMBOL TF [shuffle_seed]
"""
from __future__ import annotations

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from marketdata import load  # noqa: E402
from smv import Config, Engine  # noqa: E402
from study_nulls import shuffled  # noqa: E402

COST = {"EURUSD": 0.00010, "XAUUSD": 0.35}
PERIOD = ("2015-01-01", "2022-01-01")
SPLIT = "2019-01-01"


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]


def mean_ci(xs):
    n = len(xs)
    if n < 2:
        return None, None
    m = sum(xs) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))
    return round(m, 4), round(1.96 * sd / math.sqrt(n), 4)


def summarize(trades):
    n = len(trades)
    if n == 0:
        return {"n": 0}
    wins = sum(1 for t in trades if t["reason"] == "target1")
    be = sum(1 / (1 + t["rr1"]) for t in trades) / n     # taux de réussite « hasard »
    g, gci = mean_ci([t["r"] for t in trades])
    nt, nci = mean_ci([t["r_net"] for t in trades])
    return {"n": n, "win": round(wins / n, 4), "win_ci95": wilson(wins, n),
            "win_null_gamblers_ruin": round(be, 4),
            "mean_r_gross": g, "ci95_gross": gci, "mean_r_net": nt, "ci95_net": nci,
            "median_rr1": sorted(t["rr1"] for t in trades)[n // 2],
            "median_risk_atr": sorted(t["risk_atr"] for t in trades)[n // 2],
            "median_bars_in_trade": sorted(t["bars"] for t in trades)[n // 2]}


def run(bars, symbol):
    log = Engine(Config()).run(bars)
    created, trig = {}, {}
    trades = []
    counts = {"created": 0, "rejected": {}, "expired": {}}
    for e in log:
        if e.kind == "SETUP":
            r = e.data["rejected"]
            if r:
                counts["rejected"][r] = counts["rejected"].get(r, 0) + 1
            else:
                counts["created"] += 1
                created[e.data["setup"]] = e
        elif e.kind == "SETUP_EXPIRED":
            k = e.data["reason"]
            counts["expired"][k] = counts["expired"].get(k, 0) + 1
        elif e.kind == "SETUP_CLOSED":
            s = created[e.data["setup"]]
            risk = s.data["risk"]
            trades.append({"type": s.data["type"], "label": s.data["label"], "dir": s.direction,
                           "t": bars[s.confirm_index].t_open.isoformat(), "reason": e.data["reason"],
                           "r": e.data["r"], "r_net": e.data["r"] - COST[symbol] / risk,
                           "rr1": s.data["rr"][0], "risk_atr": s.data["risk_atr"],
                           "bars": e.data["bars_in_trade"], "mfe_r": e.data["mfe_r"]})
    out = {"counts": counts, "all": summarize(trades)}
    for typ in ("GOLDEN", "CONCEPT"):
        sub = [t for t in trades if t["type"] == typ]
        out[typ] = summarize(sub)
        out[typ + "_in"] = summarize([t for t in sub if t["t"] < SPLIT])
        out[typ + "_out"] = summarize([t for t in sub if t["t"] >= SPLIT])
    for lab in sorted({t["label"] for t in trades}):
        out["label=" + lab] = summarize([t for t in trades if t["label"] == lab])
    # sensibilité au RR : les trades à RR élevé dominent-ils le résultat ?
    for lo, hi in ((0, 1), (1, 2), (2, 4), (4, 1e9)):
        out[f"rr1_in_[{lo},{hi})"] = summarize([t for t in trades if lo <= t["rr1"] < hi])
    return out


def main():
    sym, tf = sys.argv[1], sys.argv[2]
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else None
    bars = load(sym, tf, *PERIOD)
    if seed is not None:
        bars = shuffled(bars, seed)
    res = {"symbol": sym, "tf": tf, "series": "real" if seed is None else f"shuffled{seed}",
           "bars": len(bars), "cost": COST[sym], **run(bars, sym)}
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
