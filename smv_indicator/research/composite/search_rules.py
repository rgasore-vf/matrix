"""A. Carte probabiliste : recherche en faisceau de conjonctions de 1 à 4 conditions.

- Les conditions élémentaires et leurs seuils sont dérivés de l'ENTRAÎNEMENT seulement.
- Score d'une règle = borne basse de Wilson du taux de réussite sur l'entraînement, n >= MIN_N.
- Les règles retenues sont ensuite mesurées sur la VALIDATION. Le test n'est pas lu ici.
- Contrôle : la même recherche sur des étiquettes permutées (dans chaque instrument) donne la
  hauteur du meilleur résultat « trouvé » par pur hasard avec ce volume de recherche.

Usage : python research/composite/search_rules.py DOSSIER CIBLE [permute]
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import features, load_all, split, wilson_low  # noqa: E402

BEAM = 60
DEPTH = 4
MIN_N = 1000
RECENCY_TH = (0, 3, 12, 48)


def make_conditions(train: pd.DataFrame, feats: list[str]):
    conds = []
    for f in feats:
        x = train[f]
        vals = x.dropna().unique()
        if f.startswith("s_"):
            for th in RECENCY_TH:
                conds.append((f"{f}<={th}", f, "<=", th))
            conds.append((f"{f}>=200", f, ">=", 200))
        elif len(vals) <= 8:
            for v in sorted(vals):
                conds.append((f"{f}=={v:g}", f, "==", float(v)))
        else:
            for q in (0.1, 0.25, 0.5, 0.75, 0.9):
                v = float(x.quantile(q))
                op = "<=" if q <= 0.5 else ">="
                conds.append((f"{f}{op}{v:.4g}", f, op, v))
                if q in (0.25, 0.5, 0.75):
                    op2 = ">=" if op == "<=" else "<="
                    conds.append((f"{f}{op2}{v:.4g}", f, op2, v))
    return conds


def mask(df: pd.DataFrame, c) -> np.ndarray:
    _, f, op, v = c
    x = df[f].to_numpy()
    with np.errstate(invalid="ignore"):
        if op == "<=":
            return x <= v
        if op == ">=":
            return x >= v
        return x == v


def beam_search(df: pd.DataFrame, y: np.ndarray, conds, masks):
    valid = ~np.isnan(y)
    yv = np.where(valid, y, 0.0)
    def score(m):
        m = m & valid
        n = int(m.sum())
        if n < MIN_N:
            return -1.0, n, 0.0
        k = float(yv[m].sum())
        return wilson_low(k, n), n, k / n
    level = [((), np.ones(len(df), bool))]
    found = []
    for depth in range(1, DEPTH + 1):
        cand = []
        for rule, m in level:
            used = {conds[j][1] for j in rule}
            for j, cm in enumerate(masks):
                if j in rule or conds[j][1] in used:
                    continue
                s, n, p = score(m & cm)
                if s > 0:
                    cand.append((s, tuple(sorted(rule + (j,))), n, p))
        best = {}
        for s, r, n, p in sorted(cand, key=lambda z: -z[0]):
            if r not in best:
                best[r] = (s, n, p)
            if len(best) >= BEAM:
                break
        level = []
        for r in best:
            nm = np.ones(len(df), bool)
            for j in r:
                nm &= masks[j]
            level.append((r, nm))
        found += [(depth, r, v[0], v[1], v[2]) for r, v in best.items()]
    return found


def main():
    folder, target = sys.argv[1], sys.argv[2]
    permute = len(sys.argv) > 3
    sp = split(load_all(folder))
    tr, va = sp["train"].reset_index(drop=True), sp["val"].reset_index(drop=True)
    feats = features(tr)
    conds = make_conditions(tr, feats)
    y = tr[target].to_numpy(dtype=float)
    if permute:
        rng = np.random.default_rng(1)
        y = y.copy()
        for s in tr["symbol"].unique():
            idx = np.flatnonzero((tr["symbol"] == s).to_numpy())
            y[idx] = y[rng.permutation(idx)]
    masks = [mask(tr, c) for c in conds]
    found = beam_search(tr, y, conds, masks)
    vmasks = {j: mask(va, conds[j]) for j in range(len(conds))}
    yv = va[target].to_numpy(dtype=float)
    out = []
    for depth, r, s, n, p in found:
        m = np.ones(len(va), bool)
        for j in r:
            m &= vmasks[j]
        m &= ~np.isnan(yv)
        nv = int(m.sum())
        out.append({"depth": depth, "rule": [conds[j][0] for j in r], "train_n": n,
                    "train_win": round(p, 4), "train_wilson_low": round(s, 4),
                    "val_n": nv, "val_win": round(float(yv[m].mean()), 4) if nv else None})
    base = {"train": round(float(np.nanmean(tr[target])), 4), "val": round(float(np.nanmean(va[target])), 4)}
    print(json.dumps({"target": target, "permuted": permute, "n_conditions": len(conds),
                      "base": base, "rules": out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
