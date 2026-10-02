"""Découpage et mesures de la recherche asymétrique (fixés avant l'exploration).

DEV (seule période utilisée pour chercher) : 2012-2019.
  entraînement 2012-2016, validation 2017-2019 ;
  walk-forward : (<=2014 -> 2015-16), (<=2016 -> 2017-18), (<=2018 -> 2019).
CONTAMINÉ : 2020-mars 2022, déjà observé dans la recherche précédente ; contrôle secondaire.
COFFRE-FORT : mars 2022 -> aujourd'hui, hors de cet environnement (backtest MT5 de l'utilisateur).
"""
from __future__ import annotations

import glob
import os

import numpy as np
import pandas as pd

STOPS = ("atr", "swing", "sig")
TPS = ("1", "1.5", "2", "2.5", "3", "4")
FAMILIES = ("brk20", "brk96", "fail20", "mr5", "volx", "pull", "sess", "zone", "sweep", "bos_follow", "bos_fade")
FOLDS = ((2014, (2015, 2016)), (2016, (2017, 2018)), (2018, (2019,)))
OUTCOME_PREFIX = ("r_", "mfe_", "mae_", "t_mfe_", "t_sl_")
NON_FEATURES = {"symbol", "i", "t", "year", "atr"}


def load_all(folder="/tmp/am"):
    df = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(os.path.join(folder, "*.parquet")))], ignore_index=True)
    df["day"] = (df["t"] // 86400).astype(np.int64)
    return df


def dev(df):
    return df[df["year"] <= 2019]


def features(df):
    return [c for c in df.columns if c not in NON_FEATURES and c != "day" and not c.startswith(OUTCOME_PREFIX)]


def net(df, stop, tp, cost_mult=1.0):
    return df[f"r_{stop}_{tp}"] - cost_mult * df[f"cost_{stop}"]


def stats(df, stop, tp, cost_mult=1.0):
    r = df[f"r_{stop}_{tp}"]
    m = r.notna()
    d = df[m]
    if len(d) == 0:
        return {"n": 0}
    g = r[m].to_numpy(np.float64)
    nt = net(d, stop, tp, cost_mult).to_numpy(np.float64)
    wins = nt[nt > 0].sum(); losses = -nt[nt < 0].sum()
    eq = np.cumsum(nt)
    dd = float(np.max(np.maximum.accumulate(eq) - eq)) if len(eq) else 0.0
    by_sym = d.assign(_n=nt).groupby("symbol")["_n"].mean()
    by_year = d.assign(_n=nt).groupby("year")["_n"].mean()
    # IC de l'espérance nette par rééchantillonnage de jours
    rng = np.random.default_rng(0)
    days = d["day"].to_numpy()
    u, inv = np.unique(days, return_inverse=True)
    s = np.bincount(inv, weights=nt); c = np.bincount(inv)
    bs = [s[k].sum() / c[k].sum() for k in (rng.integers(0, len(u), len(u)) for _ in range(300))]
    tpv = float(tp)
    return {"n": int(len(d)), "win": round(float((g > 0).mean()), 4),
            "breakeven_win": round(1 / (1 + tpv), 4),
            "exp_gross": round(float(g.mean()), 4), "exp_net": round(float(nt.mean()), 4),
            "exp_net_ci95": [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)],
            "pf_net": round(wins / losses, 3) if losses > 0 else None,
            "max_dd_R": round(dd, 1),
            "symbols_pos": f"{int((by_sym > 0).sum())}/{len(by_sym)}",
            "years_pos": f"{int((by_year > 0).sum())}/{len(by_year)}",
            "cost_R_med": round(float(d[f'cost_{stop}'].median()), 3),
            "risk_atr_med": round(float(d[f'risk_atr_{stop}'].median()), 2),
            "mfe_med": round(float(d[f'mfe_{stop}'].median()), 2),
            "mae_med": round(float(d[f'mae_{stop}'].median()), 2),
            "p_mfe_ge_1.5": round(float((d[f'mfe_{stop}'] >= 1.5).mean()), 3),
            "p_mfe_ge_3": round(float((d[f'mfe_{stop}'] >= 3).mean()), 3)}
