"""Verdict du coffre-fort XAU_Context (critères pré-enregistrés, docs/XAU_RESEARCH.md §5).
Usage : python research/xau/xau_vault_report.py DOSSIER_XAUCTX"""
import glob, os, sys
import numpy as np, pandas as pd
f = sys.argv[1]
sh = pd.concat([pd.read_csv(x) for x in glob.glob(os.path.join(f, "**", "*_shadow.csv"), recursive=True)], ignore_index=True)
tr_f = glob.glob(os.path.join(f, "**", "*_trades.csv"), recursive=True)
tr = pd.concat([pd.read_csv(x) for x in tr_f], ignore_index=True) if tr_f else pd.DataFrame()
sh = sh.drop_duplicates("id", keep="last")
sh["net"] = sh.r_main - sh.research_cost_R
day = pd.to_datetime(sh.sig_time_srv, format="%Y.%m.%d %H:%M").dt.floor("D").to_numpy()
rng = np.random.default_rng(0); u, inv = np.unique(day, return_inverse=True)
s, c = np.bincount(inv, weights=sh.net.to_numpy()), np.bincount(inv)
bs = [s[k].sum() / c[k].sum() for k in (rng.integers(0, len(u), len(u)) for _ in range(2000))]
ci = (np.percentile(bs, 2.5), np.percentile(bs, 97.5))
by_y = sh.groupby("year").net.mean()
real = tr.R_money.mean() if len(tr) else np.nan
print(f"shadow n={len(sh)}  espérance nette TP2 = {sh.net.mean():+.3f} R  IC95 [{ci[0]:+.3f} ; {ci[1]:+.3f}]  réussite {(sh.r_main >= 2).mean():.3f} (seuil 0,333)")
print("TP 1 / 1,5 / 2 / 3 ATR (brut):", [round(sh[c_].mean(), 3) for c_ in ("r_1", "r_1.5", "r_2", "r_3")])
print("par année:", by_y.round(3).to_dict(), "| achats/ventes:", sh.dir.value_counts().to_dict())
print(f"exécution réelle n={len(tr)}  R monétaire moyen {real:+.3f}" + (f"  swap/R {(tr.swap / tr.risk_money).mean():+.3f}" if len(tr) else ""))
pos_y = int((by_y > 0).sum())
if sh.net.mean() <= 0: v = "REJETÉ"
elif pos_y >= int(np.ceil(0.6 * len(by_y))) and real > 0:
    v = "ROBUSTE" if ci[0] > 0 else "PROMETTEUR"
else: v = "EXPLORATOIRE"
print("VERDICT :", v)
