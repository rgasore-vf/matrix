"""Candidats FIGÉS (2 octobre 2026) avant toute lecture de 2020-2022 pour ces règles.

A : H4, expansion de volatilité : amplitude des 20 bougies précédentes <= 4 ATR, bougie de signal
    d'amplitude >= 2 ATR, entrée dans le sens de la bougie à l'ouverture suivante ; SL 1 ATR ; TP 2 R.
B : idem, TP 3 R.
C : D1, BOS journalier (structure SMV) lu à l'envers ; entrée à l'ouverture suivante ; SL 1 ATR ; TP 3 R.
Sortie à l'horizon si ni TP ni SL : 96 bougies (H4), 20 bougies (D1).
"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common2 import load_all, stats

CANDS = {
    "A H4 expansion >=2 ATR, SL 1 ATR, TP 2R": ("/tmp/am_h4", lambda d: (d.f_volx == 1) & (d.range_atr >= 2), "atr", "2"),
    "B H4 expansion >=2 ATR, SL 1 ATR, TP 3R": ("/tmp/am_h4", lambda d: (d.f_volx == 1) & (d.range_atr >= 2), "atr", "3"),
    "C D1 BOS lu à l'envers, SL 1 ATR, TP 3R": ("/tmp/am_d1", lambda d: d.f_bos_fade == 1, "atr", "3"),
}

def main(include_contaminated=False):
    out = {}
    for name, (folder, f, st, tp) in CANDS.items():
        df = load_all(folder); df = df[f(df)]
        devp = df[df.year <= 2019]
        res = {"dev_by_year": {int(y): stats(g, st, tp) for y, g in devp.groupby("year")},
               "dev_by_symbol": {s: stats(g, st, tp) for s, g in devp.groupby("symbol")},
               "train_2012_2016": stats(devp[devp.year <= 2016], st, tp),
               "val_2017_2019": stats(devp[devp.year >= 2017], st, tp),
               "dev_cost_x1.5": stats(devp, st, tp, 1.5), "dev_cost_x2": stats(devp, st, tp, 2.0)}
        r = devp[f"r_{st}_{tp}"].dropna()
        res["dev_R_distribution"] = {str(k): round(float((r == k).mean()), 3) for k in (-1.0, float(tp))}
        res["dev_R_timeout_share"] = round(float(((r > -1) & (r < float(tp))).mean()), 3)
        m = devp[f"mfe_{st}"]
        res["dev_MFE_quantiles"] = {q: round(float(m.quantile(q)), 2) for q in (0.25, 0.5, 0.75, 0.9)}
        res["dev_P_MFE"] = {k: round(float((m >= k).mean()), 3) for k in (1, 1.5, 2, 3, 4)}
        if include_contaminated:
            c = df[df.year >= 2020]
            res["contaminated_2020_2022"] = stats(c, st, tp)
            res["contaminated_by_year"] = {int(y): stats(g, st, tp) for y, g in c.groupby("year")}
            res["contaminated_cost_x2"] = stats(c, st, tp, 2.0)
        out[name] = res
    print(json.dumps(out, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main(len(sys.argv) > 1 and sys.argv[1] == "contaminated")
