"""Tables de persistance (course ±1 ATR H4) par contexte, entraînement 2013-2017, validation 2018-2019,
test 2020-2022 ; puis LightGBM (précision par quantile de score) et arbre lisible."""
import sys, json
import numpy as np, pandas as pd
d = pd.read_parquet(sys.argv[1]); d = d[(d.year >= 2013) & d.r1.notna()].copy()
P = {"train 13-17": d[d.year <= 2017], "val 18-19": d[(d.year >= 2018) & (d.year <= 2019)], "test 20-22": d[d.year >= 2020]}
print("base", {k: round(v.r1.mean(), 3) for k, v in P.items()})
BINS = {"pos4": [-9, 0, .25, .5, .75, 1, 9], "leg4_atr": [0, 3, 5, 7, 10, 14, 99], "age4": [-1, 1, 3, 6, 12, 24, 999],
        "nbos4": [-1, 0, 1, 2, 4, 99], "d1_agree": [-2, -1, 0, 1], "m15_agree": [-2, -1, 0, 1], "in_zone4": [-1, 0, 1],
        "touched4": [-1, 0, 1], "opp_zone_atr": [0, 1, 2, 4, 8, 999], "prot_atr": [0, 1, 2, 3, 5, 99],
        "volr4": [0, .8, .95, 1.1, 1.3, 9], "mom4": [-99, -1, 0, 1, 2, 4, 99], "day_used": [0, .3, .6, .9, 1.2, 9],
        "hour": [-1, 6, 9, 12, 15, 18, 24]}
for col, b in BINS.items():
    t = pd.concat({k: v.groupby(pd.cut(v[col], b), observed=True).r1.agg(["mean", "count"]) for k, v in P.items()}, axis=1).round(3)
    print("\n---", col); print(t.to_string())
