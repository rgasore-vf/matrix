"""Étape 1 : chaque famille seule, chaque stop, chaque TP, sur entraînement et validation (DEV)."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common2 import FAMILIES, STOPS, TPS, dev, load_all, stats  # noqa: E402


def main():
    df = dev(load_all(sys.argv[1] if len(sys.argv) > 1 else "/tmp/am"))
    tr, va = df[df.year <= 2016], df[df.year >= 2017]
    out = []
    for f in FAMILIES + ("ALL",):
        a = tr if f == "ALL" else tr[tr["f_" + f] == 1]
        b = va if f == "ALL" else va[va["f_" + f] == 1]
        for s in STOPS:
            for k in TPS:
                out.append({"family": f, "stop": s, "tp": k, "train": stats(a, s, k), "val": stats(b, s, k)})
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
