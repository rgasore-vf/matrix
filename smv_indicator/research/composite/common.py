"""Découpage et utilitaires communs de la recherche composite (fixés AVANT l'exploration)."""
from __future__ import annotations

import glob
import math
import os

import numpy as np
import pandas as pd

HOLD_SYMS = ("USDCAD", "EURCHF", "GBPJPY")        # jamais vus en entraînement ni validation
TRAIN_END = 2017                                   # entraînement : 2012-2017
VAL_YEARS = (2018, 2019)                           # validation : 2018-2019
TEST_START = 2020                                  # test : 2020-mars 2022 + symboles réservés

TARGETS = ["y_1.0_1.0", "y_1.5_1.0", "y_2.0_1.0", "y_1.0_0.5", "y_0.5_1.0", "y_2.0_2.0"]
GEOM = {"y_1.0_1.0": (1.0, 1.0), "y_1.5_1.0": (1.5, 1.0), "y_2.0_1.0": (2.0, 1.0),
        "y_1.0_0.5": (1.0, 0.5), "y_0.5_1.0": (0.5, 1.0), "y_2.0_2.0": (2.0, 2.0)}
NON_FEATURES = {"symbol", "i", "t", "year", "atr", "cost_atr", "y_mfe48", "y_mae48"}


def load_all(folder: str) -> pd.DataFrame:
    df = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(os.path.join(folder, "*.parquet")))],
                   ignore_index=True)
    df["day"] = (df["t"] // 86400).astype(np.int64)
    return df


def apply_hours(df: pd.DataFrame) -> pd.DataFrame:
    """Filtre d'heures via la variable d'environnement SMV_HOURS (ex. « 1-19 », heure de Paris).
    Les heures 20 h-0 h (rollover de New York) ont des spreads réels bien supérieurs au coût
    modélisé : la recherche principale les exclut (voir COMPOSITE_RESEARCH.md)."""
    spec = os.environ.get("SMV_HOURS")
    if not spec:
        return df
    a, b = (int(x) for x in spec.split("-"))
    return df[(df["hour"] >= a) & (df["hour"] <= b)]


def split(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    df = apply_hours(df)
    hold = df["symbol"].isin(HOLD_SYMS)
    return {
        "train": df[~hold & (df["year"] <= TRAIN_END)],
        "val": df[~hold & df["year"].isin(VAL_YEARS)],
        "test_time": df[~hold & (df["year"] >= TEST_START)],
        "test_syms": df[hold],
    }


def features(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c not in NON_FEATURES and not c.startswith("y_")
            and not c.startswith("t_") and c != "day"]


def wilson_low(k: float, n: int, z: float = 1.96) -> float:
    if n == 0:
        return 0.0
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    return (c - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d


def expectancy(win: np.ndarray, target: str, cost_atr: np.ndarray, cost_mult: float = 1.0) -> float:
    """Espérance en R (R = distance du stop) ; même bougie = perte ; coût aller-retour déduit."""
    tp, sl = GEOM[target]
    r = np.where(win == 1, tp / sl, -1.0) - cost_mult * cost_atr / sl
    return float(np.mean(r)) if len(r) else float("nan")


def day_bootstrap_ci(win: np.ndarray, days: np.ndarray, reps: int = 500, seed: int = 0):
    """Intervalle à 95 % du taux de réussite par rééchantillonnage de JOURS entiers
    (les opportunités d'un même jour sont corrélées)."""
    rng = np.random.default_rng(seed)
    u, inv = np.unique(days, return_inverse=True)
    k = np.bincount(inv, weights=win); n = np.bincount(inv)
    stats = []
    for _ in range(reps):
        s = rng.integers(0, len(u), len(u))
        stats.append(k[s].sum() / max(1, n[s].sum()))
    return float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5))


def report(sub: pd.DataFrame, target: str, cost_mults=(0.0, 1.0, 2.0)) -> dict:
    s = sub[sub[target].notna()]
    w = s[target].to_numpy(dtype=np.float64)
    out = {"n": int(len(s)), "win": round(float(w.mean()), 4) if len(s) else None}
    if len(s) == 0:
        return out
    lo, hi = day_bootstrap_ci(w, s["day"].to_numpy())
    out["ci95_days"] = [round(lo, 4), round(hi, 4)]
    for m in cost_mults:
        out[f"exp_R_cost{m:g}"] = round(expectancy(w, target, s["cost_atr"].to_numpy(), m), 4)
    tp, sl = GEOM[target]
    gains = (w * tp / sl).sum(); losses = ((1 - w) * 1.0).sum()
    out["profit_factor_nocost"] = round(gains / losses, 3) if losses else None
    by_sym = s.groupby("symbol")[target].mean()
    out["symbols_above_null"] = f"{int((by_sym > sl / (tp + sl)).sum())}/{len(by_sym)}"
    by_year = s.groupby("year")[target].mean()
    out["years_above_null"] = f"{int((by_year > sl / (tp + sl)).sum())}/{len(by_year)}"
    return out
