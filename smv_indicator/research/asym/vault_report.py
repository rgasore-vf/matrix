"""Lecture des journaux de l'EA ASYM_Vault et verdict selon les critères PRÉ-ENREGISTRÉS
(docs/ASYM_RESEARCH.md §9, écrits avant toute lecture du coffre-fort).

Usage : python research/asym/vault_report.py DOSSIER_DES_CSV [SORTIE.json]
Le dossier contient les fichiers *_shadow.csv, *_trades.csv, *_signals.csv, *_log.csv de l'EA
(MQL5 Files commun : %APPDATA%/MetaQuotes/Terminal/Common/Files/ASYM).
"""
from __future__ import annotations

import glob
import json
import os
import sys

import numpy as np
import pandas as pd

DEV = {"A_H4_EXPANSION_2R": 0.03, "B_H4_EXPANSION_3R": 0.09, "C_D1_BOSFADE_3R": 0.10}


def boot_ci(vals, days, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    u, inv = np.unique(days, return_inverse=True)
    s, c = np.bincount(inv, weights=vals), np.bincount(inv)
    bs = []
    for _ in range(n):
        k = rng.integers(0, len(u), len(u))
        bs.append(s[k].sum() / c[k].sum())
    return [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)]


def load(folder, kind):
    fs = sorted(glob.glob(os.path.join(folder, "**", f"*_{kind}.csv"), recursive=True))
    dfs = [pd.read_csv(f) for f in fs]
    dfs = [d for d in dfs if len(d)]
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def summarize_shadow(g):
    g = g.copy()
    g["net"] = g["r_main"] - g["research_cost_R"]
    g["net_x2"] = g["r_main"] - 2 * g["research_cost_R"]
    g["net_spread"] = g["r_main"] - g["spread_R_at_signal"]
    g["day"] = pd.to_datetime(g["sig_time_srv"], format="%Y.%m.%d %H:%M").dt.floor("D")
    tp = 2.0 if g["strategy"].iloc[0].endswith("2R") else 3.0
    by_sym = g.groupby("symbol")["net"].mean()
    by_year = g.groupby("year")["net"].mean()
    out = {
        "n": int(len(g)),
        "win": round(float((g["r_main"] > 0).mean()), 4),
        "breakeven_win": round(1 / (1 + tp), 4),
        "exp_gross": round(float(g["r_main"].mean()), 4),
        "exp_net_research_cost": round(float(g["net"].mean()), 4),
        "exp_net_ci95": boot_ci(g["net"].to_numpy(), g["day"].to_numpy()),
        "exp_net_cost_x2": round(float(g["net_x2"].mean()), 4),
        "exp_net_spread_at_signal": round(float(g["net_spread"].mean()), 4),
        "symbols_pos": f"{int((by_sym > 0).sum())}/{len(by_sym)}",
        "years_pos": f"{int((by_year > 0).sum())}/{len(by_year)}",
        "by_symbol": {k: round(float(v), 4) for k, v in by_sym.items()},
        "by_year": {int(k): round(float(v), 4) for k, v in by_year.items()},
        "n_by_symbol": {k: int(v) for k, v in g.groupby("symbol").size().items()},
        "mfe_median": round(float(g["mfe_R"].median()), 3),
        "p_mfe_ge": {k: round(float((g["mfe_R"] >= k).mean()), 3) for k in (1, 2, 3, 4, 8)},
        "exp_gross_by_tp": {c[2:]: round(float(g[c].mean()), 4) for c in g.columns if c.startswith("r_") and c != "r_main"},
    }
    eq = np.cumsum(g.sort_values("sig_time_srv")["net"].to_numpy())
    out["max_dd_R"] = round(float(np.max(np.maximum.accumulate(eq) - eq)), 1) if len(eq) else 0.0
    return out


def summarize_trades(t):
    if t.empty:
        return {"n": 0}
    return {
        "n": int(len(t)),
        "exp_R_money": round(float(t["R_money"].mean()), 4),
        "exp_R_price": round(float(t["R_price"].mean()), 4),
        "win": round(float((t["net_money"] > 0).mean()), 4),
        "net_money": round(float(t["net_money"].sum()), 2),
        "exit_reasons": {k: int(v) for k, v in t["exit_reason"].value_counts().items()},
        "slip_R_mean": round(float(t["slip_R"].mean()), 4),
        "spread_pts_median": float(t["spread_pts_entry"].median()),
        "by_symbol_R_money": {k: round(float(v), 4) for k, v in t.groupby("symbol")["R_money"].mean().items()},
        "by_year_R_money": {int(k): round(float(v), 4) for k, v in t.groupby("year")["R_money"].mean().items()},
    }


def verdict(s, t):
    """Critères pré-enregistrés (ASYM_RESEARCH.md §9)."""
    if s["n"] == 0:
        return "AUCUNE DONNÉE"
    pos_sym = int(s["symbols_pos"].split("/")[0]); n_sym = int(s["symbols_pos"].split("/")[1])
    pos_y = int(s["years_pos"].split("/")[0]); n_y = int(s["years_pos"].split("/")[1])
    if s["exp_net_research_cost"] <= 0:
        return "REJETÉ"
    broad = pos_sym >= int(np.ceil(7 / 12 * n_sym)) and pos_y >= int(np.ceil(3 / 5 * n_y))
    real_ok = t.get("n", 0) > 0 and t["exp_R_money"] > 0
    if not (broad and real_ok):
        return "EXPLORATOIRE"
    if s["exp_net_ci95"][0] > 0 and s["exp_net_cost_x2"] > 0:
        return "ROBUSTE"
    return "PROMETTEUR"


def main():
    folder = sys.argv[1]
    sh, tr = load(folder, "shadow"), load(folder, "trades")
    if sh.empty:
        print("aucun fichier *_shadow.csv non vide")
        return
    # doublons possibles si un symbole a été testé deux fois : garder le dernier
    sh = sh.drop_duplicates(subset=["id", "strategy"], keep="last")
    sh = sh[pd.to_datetime(sh["sig_time_srv"], format="%Y.%m.%d %H:%M") >= "2022-03-01"]
    out = {}
    for strat, g in sh.groupby("strategy"):
        t = tr[tr["strategy"] == strat] if not tr.empty else pd.DataFrame()
        if not t.empty:
            t = t.drop_duplicates(subset=["id"], keep="last")
        s, ts = summarize_shadow(g), summarize_trades(t)
        out[strat] = {"dev_exp_net": DEV.get(strat), "shadow": s, "real": ts, "verdict": verdict(s, ts)}
    txt = json.dumps(out, ensure_ascii=False, indent=1)
    print(txt)
    if len(sys.argv) > 2:
        with open(sys.argv[2], "w") as f:
            f.write(txt)


if __name__ == "__main__":
    main()
