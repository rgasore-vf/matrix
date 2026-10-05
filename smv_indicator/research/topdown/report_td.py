"""Rapport exploratoire de la méthode combinée (build_td.py) : ce que le prix donne, sans cible imposée.

Pour chaque configuration (zone H4 ou H1, entrée M15) et chaque variante de séquence :
  - nombre de trades, trades par jour (par instrument et pour le panier de 12) ;
  - « combien de R sont atteints » : P(MFE >= k) avant le stop, comparé au hasard 1/(1+k)
    (marche aléatoire sans dérive : probabilité d'atteindre +k avant -1) ;
  - espérance pour des TP fixes 1 à 5 R, brute et nette du coût nominal ;
  - cibles « premier intact » M15 et HTF ;
  - heures (Paris) : nombre de trades et espérance, pour décider plus tard des horaires ;
  - stabilité par année et par instrument.
Périodes séparées : 2012-2019 (développement) et 2020-2022.
Usage : python research/topdown/report_td.py DOSSIER [SORTIE.json]
"""
from __future__ import annotations

import glob
import json
import os
import sys

import numpy as np
import pandas as pd

TPS = ("1", "1.5", "2", "3", "4", "5")
MFE_K = (1, 2, 3, 4, 5, 6, 8, 10)
VARIANTS = {"toutes (zone HTF + BOS M15)": lambda d: d,
            "avec prise de liquidité": lambda d: d[d.has_sweep == 1],
            "séquence complète (fail puis prise)": lambda d: d[d.strict == 1]}


def load(folder):
    fs = sorted(glob.glob(os.path.join(folder, "*.parquet")))
    return pd.concat([pd.read_parquet(f) for f in fs if os.path.getsize(f) > 0], ignore_index=True)


def block(d, days_total):
    if len(d) == 0:
        return {"n": 0}
    out = {"n": int(len(d)),
           "trades_par_jour_panier": round(len(d) / days_total, 2),
           "trades_par_jour_par_instrument": round(len(d) / days_total / d.symbol.nunique(), 3),
           "risque_pips_median": round(float(d.risk_pips.median()), 1),
           "cout_R_median": round(float(d.cost_R.median()), 3),
           "MFE_R_moyen": round(float(d.mfe_R.mean()), 2),
           "MFE_R_median": round(float(d.mfe_R.median()), 2),
           "P_MFE_ge_k": {k: [round(float((d.mfe_R >= k).mean()), 3), round(1 / (1 + k), 3)] for k in MFE_K},
           "sans_cible_R_net": round(float((d.end_R - d.cost_R).mean()), 3),
           "TP_fixes": {}}
    for k in TPS:
        r = d[f"r_tp{k}"]
        net = r - d.cost_R
        out["TP_fixes"][k] = {"reussite": round(float((r >= float(k) - 1e-9).mean()), 3),
                              "seuil": round(1 / (1 + float(k)), 3),
                              "esp_brute": round(float(r.mean()), 3), "esp_nette": round(float(net.mean()), 3)}
    for t in ("tgt1", "tgtH"):
        if f"r_{t}" in d:
            m = d[f"r_{t}"].notna()
            if m.any():
                x = d[m]
                out[f"cible_{t}"] = {"n": int(m.sum()), "distance_R_mediane": round(float(x[f"{t}_R"].median()), 2),
                                     "atteinte": round(float((x[f"r_{t}"] >= x[f"{t}_R"] - 1e-9).mean()), 3),
                                     "esp_nette": round(float((x[f"r_{t}"] - x.cost_R).mean()), 3)}
    return out


def detail(d, k="3"):
    net = d[f"r_tp{k}"] - d.cost_R
    return {"par_annee": {int(y): [int(len(g)), round(float((g[f"r_tp{k}"] - g.cost_R).mean()), 3)] for y, g in d.groupby("year")},
            "par_instrument": {s: [int(len(g)), round(float((g[f"r_tp{k}"] - g.cost_R).mean()), 3)] for s, g in d.groupby("symbol")},
            "par_heure_paris": {int(h): [int(len(g)), round(float((g[f"r_tp{k}"] - g.cost_R).mean()), 3),
                                         round(float((g.mfe_R >= 3).mean()), 3)] for h, g in d.groupby("hour")},
            "esp_nette_TP": k, "esp_nette_globale": round(float(net.mean()), 3)}


def main():
    df = load(sys.argv[1])
    # jours de marché : jours distincts où au moins une bougie existe ~ jours ouvrés de la période
    res = {}
    for htf, g in df.groupby("htf"):
        cfg = f"zone {'H4' if htf == 240 else 'H1'} / entrée M15"
        res[cfg] = {}
        for per, gp in (("2012-2019", g[g.year <= 2019]), ("2020-2022", g[g.year >= 2020])):
            days = pd.bdate_range(gp.date.min(), gp.date.max()).size if len(gp) else 1
            res[cfg][per] = {}
            for name, f in VARIANTS.items():
                sub = f(gp)
                res[cfg][per][name] = block(sub, days)
                if name.startswith("toutes") and len(sub):
                    res[cfg][per][name]["detail_TP3"] = detail(sub, "3")
    txt = json.dumps(res, ensure_ascii=False, indent=1)
    print(txt)
    if len(sys.argv) > 2:
        open(sys.argv[2], "w").write(txt)


if __name__ == "__main__":
    main()
