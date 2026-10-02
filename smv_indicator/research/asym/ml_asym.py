"""Étape 2 : LightGBM en régression sur le R NET (après coûts) pour un couple (stop, TP).

Sorties (DEV uniquement) :
- courbe espérance nette / couverture sur la validation (seuils fixés sur la validation) ;
- walk-forward : 3 plis, modèle entraîné sur le passé, évalué sur la période suivante ;
- leave-one-symbol-out : pour chaque instrument, modèle entraîné sur les 11 autres
  (années d'entraînement), évalué sur cet instrument (années de validation) ;
- importance des variables ; arbre de régression lisible (profondeur 4).
Usage : python research/asym/ml_asym.py DOSSIER STOP TP SORTIE_DIR
"""
from __future__ import annotations

import json
import os
import pickle
import sys

import lightgbm as lgb
import numpy as np
from sklearn.tree import DecisionTreeRegressor, _tree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common2 import FOLDS, dev, features, load_all, net  # noqa: E402

COV = (1.0, 0.5, 0.25, 0.1, 0.05, 0.02)
PARAMS = dict(n_estimators=600, learning_rate=0.05, num_leaves=31, min_child_samples=1000, subsample=0.7,
              subsample_freq=1, colsample_bytree=0.7, reg_lambda=10.0, verbose=-1, n_jobs=4)


def fit(Xt, yt, Xv=None, yv=None):
    m = lgb.LGBMRegressor(**PARAMS)
    if Xv is not None:
        m.fit(Xt, yt, eval_set=[(Xv, yv)], callbacks=[lgb.early_stopping(100, verbose=False)])
    else:
        m.fit(Xt, yt)
    return m


def curve(score, y, win, thr=None):
    out = []
    order = np.sort(score)[::-1]
    for c in COV:
        t = thr[c] if thr is not None else order[max(1, int(len(score) * c)) - 1]
        m = score >= t
        out.append({"cov": c, "n": int(m.sum()), "exp_net": round(float(y[m].mean()), 4) if m.any() else None,
                    "win": round(float(win[m].mean()), 4) if m.any() else None})
    return out


def tree_rules(tree, feats, Xv, yv):
    t = tree.tree_
    leaves = tree.apply(Xv)
    res = []
    def walk(node, conds):
        if t.feature[node] == _tree.TREE_UNDEFINED:
            m = leaves == node
            res.append({"rule": conds, "train_n": int(t.n_node_samples[node]), "train_exp": round(float(t.value[node][0][0]), 4),
                        "val_n": int(m.sum()), "val_exp": round(float(yv[m].mean()), 4) if m.any() else None})
            return
        f, th = feats[t.feature[node]], t.threshold[node]
        walk(t.children_left[node], conds + [f"{f}<={th:.4g}"]); walk(t.children_right[node], conds + [f"{f}>{th:.4g}"])
    walk(0, [])
    return sorted(res, key=lambda r: -(r["val_exp"] if r["val_exp"] is not None else -9))


def main():
    folder, stop, tp, outdir = sys.argv[1:5]
    os.makedirs(outdir, exist_ok=True)
    df = dev(load_all(folder))
    col = f"r_{stop}_{tp}"
    df = df[df[col].notna()].copy()
    df["y"] = net(df, stop, tp).astype(np.float64)
    df["win"] = (df[col] > 0).astype(float)
    feats = features(df.drop(columns=["y", "win"]))
    tr, va = df[df.year <= 2016], df[df.year >= 2017]
    Xt, Xv = tr[feats].to_numpy(np.float32), va[feats].to_numpy(np.float32)
    m = fit(Xt, tr.y.to_numpy(), Xv, va.y.to_numpy())
    sv = m.predict(Xv)
    srt = np.sort(sv)[::-1]
    thr = {c: float(srt[max(1, int(len(sv) * c)) - 1]) for c in COV}
    res = {"stop": stop, "tp": tp, "best_iter": int(m.best_iteration_ or 0),
           "base_val_exp_net": round(float(va.y.mean()), 4),
           "curve_val": curve(sv, va.y.to_numpy(), va.win.to_numpy(), thr)}
    # walk-forward (nombre d'arbres fixé par le modèle principal)
    nb = max(50, int(m.best_iteration_ or 300))
    wf = []
    for end, years in FOLDS:
        a, b = df[df.year <= end], df[df.year.isin(years)]
        mm = lgb.LGBMRegressor(**{**PARAMS, "n_estimators": nb}).fit(a[feats].to_numpy(np.float32), a.y.to_numpy())
        sb = mm.predict(b[feats].to_numpy(np.float32))
        wf.append({"train_end": end, "test_years": list(years), "curve": curve(sb, b.y.to_numpy(), b.win.to_numpy())})
    res["walk_forward"] = wf
    # leave-one-symbol-out
    loso = []
    for sym in sorted(df.symbol.unique()):
        a = tr[tr.symbol != sym]; b = va[va.symbol == sym]
        mm = lgb.LGBMRegressor(**{**PARAMS, "n_estimators": nb}).fit(a[feats].to_numpy(np.float32), a.y.to_numpy())
        sb = mm.predict(b[feats].to_numpy(np.float32))
        loso.append({"symbol": sym, "curve": curve(sb, b.y.to_numpy(), b.win.to_numpy())})
    res["loso"] = loso
    imp = sorted(zip(feats, m.booster_.feature_importance("gain")), key=lambda z: -z[1])
    res["top_features"] = [(f, round(float(g), 1)) for f, g in imp[:25]]
    tree = DecisionTreeRegressor(max_depth=4, min_samples_leaf=3000).fit(np.nan_to_num(Xt, nan=-999), tr.y.to_numpy())
    res["tree"] = tree_rules(tree, feats, np.nan_to_num(Xv, nan=-999), va.y.to_numpy())
    with open(os.path.join(outdir, f"asym_{stop}_{tp}.pkl"), "wb") as fh:
        pickle.dump({"model": m, "feats": feats, "thr": thr}, fh)
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
