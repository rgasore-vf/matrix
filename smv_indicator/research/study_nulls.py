"""Contrôle des modèles nuls : mêmes mesures sur des séries dont l'ordre des bougies est mélangé.

Le mélange conserve la distribution des bougies (corps, mèches, amplitude) mais détruit toute
dépendance temporelle. Si une mesure donne le même « excès » sur la série mélangée, cet excès
vient de la méthode de mesure, pas du marché.
"""
from __future__ import annotations

import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from marketdata import load  # noqa: E402
from smv import Config  # noqa: E402
from smv.types import Bar  # noqa: E402
from study_outcomes import study_structure, study_zones  # noqa: E402


def shuffled(bars, seed):
    rng = random.Random(seed)
    parts = [(b.close - b.open, b.high - max(b.open, b.close), min(b.open, b.close) - b.low) for b in bars]
    rng.shuffle(parts)
    out = []
    p = bars[0].open
    for i, (dc, uw, lw) in enumerate(parts):
        o, c = p, p + dc
        out.append(Bar(i, bars[i].t_open, bars[i].t_close, o, max(o, c) + uw, min(o, c) - lw, c))
        p = c
    return out


def main():
    res = {}
    for sym in ("EURUSD", "XAUUSD"):
        h1 = load(sym, "h1", "2015-01-01", "2022-01-01")
        r = {}
        for s in (1, 2):
            sh = shuffled(h1, s)
            r[f"seed{s}"] = {"structure_A": study_structure(sh, "A"),
                             "zones_bosorigin": {k: v for k, v in study_zones(sh, Config()).items()
                                                 if k in ("all", "source=BOS_CHANGE", "source=BOS_CONTINUATION")},
                             "zones_allpivots": {k: v for k, v in study_zones(sh, Config(zones_on="all_pivots")).items()
                                                 if k in ("all", "source=PIVOT")}}
        res[sym] = r
        print(sym, "done", file=sys.stderr)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
