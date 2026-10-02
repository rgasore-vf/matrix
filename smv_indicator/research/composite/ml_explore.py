"""B. Exploration non linéaire : LightGBM + arbre de décision lisible.

- Apprentissage sur l'entraînement, arrêt précoce sur la validation.
- Courbes précision / couverture sur entraînement et validation : on garde les X % des
  opportunités les mieux notées (X = 50, 25, 10, 5, 2, 1) ; les seuils de score sont fixés
  sur la validation et enregistrés pour être appliqués tels quels au test (script final).
- Arbre de décision (profondeur 5, feuilles >= 1 000 cas) pour traduire les interactions en
  règles ; feuilles classées par précision de validation.
- Le test n'est PAS lu ici.

Usage : python research/composite/ml_explore.py DOSSIER CIBLE SORTIE_DIR
"""
from __future__ import annotations

import json
import os
import pickle
import sys

import lightgbm as lgb
import numpy as np
from sklearn.tree import DecisionTreeClassifier, _tree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import features, load_all, split  # noqa: E402

COVERAGES = (1.0, 0.5, 0.25, 0.10, 0.05, 0.02, 0.01)


def curve(score, y, thresholds=None):
    order = np.argsort(-score)
    out = []
    for c in COVERAGES:
        if thresholds is not None:
            m = score >= thresholds[c]
        else:
            m = np.zeros(len(score), bool)
            m[order[:max(1, int(len(score) * c))]] = True
        out.append({"coverage_target": c, "n": int(m.sum()), "win": round(float(y[m].mean()), 4) if m.any() else None})
    return out


def tree_rules(clf, feats, Xv, yv):
    t = clf.tree_
    leaves = clf.apply(Xv)
    rules = []
    def walk(node, conds):
        if t.feature[node] == _tree.TREE_UNDEFINED:
            m = leaves == node
            rules.append({"rule": conds, "train_n": int(t.n_node_samples[node]),
                          "train_win": round(float(t.value[node][0][1] / t.value[node][0].sum()), 4),
                          "val_n": int(m.sum()), "val_win": round(float(yv[m].mean()), 4) if m.any() else None})
            return
        f, th = feats[t.feature[node]], t.threshold[node]
        walk(t.children_left[node], conds + [f"{f}<={th:.4g}"])
        walk(t.children_right[node], conds + [f"{f}>{th:.4g}"])
    walk(0, [])
    return sorted(rules, key=lambda r: -(r["val_win"] or 0))


def main():
    folder, target, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(outdir, exist_ok=True)
    sp = split(load_all(folder))
    tr = sp["train"][sp["train"][target].notna()]
    va = sp["val"][sp["val"][target].notna()]
    feats = features(tr)
    Xt, yt = tr[feats].to_numpy(np.float32), tr[target].to_numpy()
    Xv, yv = va[feats].to_numpy(np.float32), va[target].to_numpy()
    model = lgb.LGBMClassifier(n_estimators=2000, learning_rate=0.02, num_leaves=31, min_child_samples=500,
                               subsample=0.7, subsample_freq=1, colsample_bytree=0.7, reg_lambda=5.0,
                               verbose=-1, n_jobs=4)
    model.fit(Xt, yt, eval_set=[(Xv, yv)], eval_metric="binary_logloss",
              callbacks=[lgb.early_stopping(100, verbose=False)])
    st, sv = model.predict_proba(Xt)[:, 1], model.predict_proba(Xv)[:, 1]
    order = np.sort(sv)[::-1]
    thresholds = {c: float(order[max(1, int(len(sv) * c)) - 1]) for c in COVERAGES}
    imp = sorted(zip(feats, model.booster_.feature_importance("gain")), key=lambda z: -z[1])
    tree = DecisionTreeClassifier(max_depth=5, min_samples_leaf=1000).fit(np.nan_to_num(Xt, nan=-999), yt)
    res = {"target": target, "base": {"train": round(float(yt.mean()), 4), "val": round(float(yv.mean()), 4)},
           "best_iteration": int(model.best_iteration_ or 0),
           "curve_train": curve(st, yt), "curve_val": curve(sv, yv, thresholds),
           "top_features": [(f, round(float(g), 1)) for f, g in imp[:25]],
           "tree_leaves": tree_rules(tree, feats, np.nan_to_num(Xv, nan=-999), yv)[:12]}
    with open(os.path.join(outdir, f"model_{target}.pkl"), "wb") as fh:
        pickle.dump({"model": model, "feats": feats, "thresholds": thresholds, "tree": tree}, fh)
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
