"""Évaluation finale, UNE SEULE FOIS, des candidats figés avant lecture du test.

Candidats figés le 2 octobre 2026 après exploration sur entraînement et validation :
  C1a/C1b : LightGBM toutes heures, cible ±1 ATR, top 2 % / 1 % (seuils de validation)
  C2      : règle « z_age>=18 & wick_against_atr<=0.2807 & hour>=21 » (rollover)
  C3      : LightGBM heures liquides (1 h-19 h Paris), ±1 ATR, top 5 %
  C4      : LightGBM heures liquides, TP 0,5 / SL 1, top 1 %
  C5      : séquence SMV (heures liquides) : 1re touche zone décisionnelle + liquidité opposée
            prise <= 12 + prise de borne <= 48 + zone fraîche <= 48 + H1 aligné + pénétration <= 0,5
  C6      : LightGBM heures liquides, TP 2 / SL 2, top 5 %
Usage : python research/composite/final_eval.py DOSSIER_MATRICES DOSSIER_MODELES > results.json
"""
from __future__ import annotations

import json
import os
import pickle
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_all, report  # noqa: E402
from common import HOLD_SYMS, TEST_START, TRAIN_END, VAL_YEARS  # noqa: E402


def parts(df):
    hold = df["symbol"].isin(HOLD_SYMS)
    return {"train": df[~hold & (df["year"] <= TRAIN_END)], "val": df[~hold & df["year"].isin(VAL_YEARS)],
            "test_time": df[~hold & (df["year"] >= TEST_START)], "test_syms": df[hold]}


def liquid(d):
    return d[(d["hour"] >= 1) & (d["hour"] <= 19)]


def ml_select(path, cov):
    m = pickle.load(open(path, "rb"))
    def f(d):
        s = m["model"].predict_proba(d[m["feats"]].to_numpy(np.float32))[:, 1]
        return d[s >= m["thresholds"][cov]]
    return f


def main():
    mdir = sys.argv[2]
    df = load_all(sys.argv[1])
    P = parts(df)
    cands = {
        "C1a ML toutes heures ±1 ATR top 2%": ("y_1.0_1.0", ml_select(f"{mdir}/model_y_1.0_1.0.pkl", 0.02), False),
        "C1b ML toutes heures ±1 ATR top 1%": ("y_1.0_1.0", ml_select(f"{mdir}/model_y_1.0_1.0.pkl", 0.01), False),
        "C2 règle rollover": ("y_1.0_1.0", lambda d: d[(d.z_age >= 18) & (d.wick_against_atr <= 0.2807) & (d.hour >= 21)], False),
        "C3 ML heures liquides ±1 ATR top 5%": ("y_1.0_1.0", ml_select(f"{mdir}/liquid/model_y_1.0_1.0.pkl", 0.05), True),
        "C4 ML heures liquides TP0.5/SL1 top 1%": ("y_0.5_1.0", ml_select(f"{mdir}/liquid/model_y_0.5_1.0.pkl", 0.01), True),
        "C5 séquence SMV": ("y_1.0_1.0", lambda d: d[(d.trg_zone == 1) & (d.z_src == 3) & (d.s_LIQ_CLEAN_opp <= 12)
                                                    & ((d.s_RS_STB_opp <= 48) | (d.s_RS_SPRING_opp <= 48) | (d.s_RS_UT_opp <= 48) | (d.s_RS_UTAD_opp <= 48))
                                                    & (d.z_age <= 48) & (d.h1_trend == 1) & (d.z_pen <= 0.5)], True),
        "C6 ML heures liquides TP2/SL2 top 5%": ("y_2.0_2.0", ml_select(f"{mdir}/liquid/model_y_2.0_2.0.pkl", 0.05), True),
    }
    out = {}
    for name, (target, sel, liq) in cands.items():
        out[name] = {"target": target}
        for p, d in P.items():
            d = liquid(d) if liq else d
            out[name][p] = report(sel(d), target, cost_mults=(0.0, 1.0, 2.0, 3.0))
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
