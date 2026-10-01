"""Agrège les sorties de research/modules.py (12 instruments x M15/H1, réel et mélangé).

Pour chaque concept : taux de réussite de la course ±k ATR (k = 1 et 2), réel et mélangé,
excès du réel sur 50 % avec intervalle à 95 % (binomial, observations supposées indépendantes,
hypothèse optimiste), et nombre d'instruments où le réel dépasse 50 %.
Usage : python research/modules_report.py DOSSIER > research/results_modules.json
"""
from __future__ import annotations

import glob
import json
import math
import os
import sys
from collections import defaultdict


def main(folder: str) -> None:
    agg = defaultdict(lambda: {"real": [0, 0.0], "shuf": [0, 0.0], "pos": 0, "inst": 0})
    liq = defaultdict(lambda: {"real": [0, 0.0], "shuf": [0, 0.0]})
    ce = defaultdict(list)
    for f in glob.glob(os.path.join(folder, "*_*_*.json")):
        d = json.load(open(f))
        kind = "real" if d["series"] == "real" else "shuf"
        for name, v in d["signals"].items():
            for k in ("1", "2"):
                n, w = v["n" + k], v["w" + k]
                if n == 0:
                    continue
                a = agg[(d["tf"], k, name)]
                a[kind][0] += n
                a[kind][1] += w
                if kind == "real":
                    a["inst"] += 1
                    a["pos"] += int(w / n > 0.5)
        for name, v in d["liquidity"].items():
            g = liq[(d["tf"], name)]
            g[kind][0] += v["n"]
            g[kind][1] += v["n"] * v["taken"]
        if "spearman" in d["cause_effect"]:
            ce[(d["tf"], kind)].append(d["cause_effect"])
    out = {"signals": [], "liquidity": [], "cause_effect": {}}
    for (tf, k, name), a in sorted(agg.items()):
        nr, wr = a["real"]
        ns, ws = a["shuf"]
        if nr == 0:
            continue
        p = wr / nr
        half = 1.96 * math.sqrt(0.25 / nr)
        out["signals"].append({"tf": tf, "k_atr": int(k), "concept": name, "n": nr,
                               "win_real": round(p, 4), "ci95": round(half, 4),
                               "win_shuffled": round(ws / ns, 4) if ns else None,
                               "instruments_above_50": f"{a['pos']}/{a['inst']}"})
    for (tf, name), g in sorted(liq.items()):
        nr, sr = g["real"]
        ns, ss = g["shuf"]
        out["liquidity"].append({"tf": tf, "group": name, "n": nr,
                                 "taken_real": round(sr / nr, 4) if nr else None,
                                 "taken_shuffled": round(ss / ns, 4) if ns else None})
    for (tf, kind), lst in ce.items():
        n = sum(x["n"] for x in lst)
        out["cause_effect"][f"{tf}_{kind}"] = {
            "n": n, "spearman_mean": round(sum(x["spearman"] * x["n"] for x in lst) / n, 4),
            "effect_short": round(sum(x["effect_short_causes"] * x["n"] for x in lst) / n, 3),
            "effect_long": round(sum(x["effect_long_causes"] * x["n"] for x in lst) / n, 3)}
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/mod")
