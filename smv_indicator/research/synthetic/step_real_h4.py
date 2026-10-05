"""Step Index réel (Deriv, 3 000 bougies H4, mai 2025 -> oct. 2026, exportées par l'EA du coffre-fort).
Sans M15, on monte la stratégie d'un cran : direction = structure D1 (agrégée depuis les H4, marché 24/7),
entrées = BOS H4 dans ce sens, entrée au retour sur la zone (bougie manipulatrice / bougie qui prend
l'argent), stop à la mèche ; issues TP 2 R / 3 R, MFE sur 96 bougies H4.
Plus la persistance de la tendance D1 (course ±1 ATR D1 sur 20 bougies H4... voir code).
Témoin : 200 séries simulées de même longueur (marche aléatoire ±0,1 par seconde) passées dans le même code."""
import os, sys, glob
from datetime import datetime, timedelta, timezone
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("..", "../..", "../daystudy"): sys.path.insert(0, os.path.join(HERE, p))
from smv.types import Bar
from smv import Config, Engine
from smv.mtf import resample
import build_day as BD

def real_bars():
    b = pd.read_csv(os.path.join(HERE, "data", "StepIndex_H4_deriv.csv"))
    out = []
    for k, r in enumerate(b.itertuples()):
        t = datetime.strptime(r.time_srv, "%Y.%m.%d %H:%M").replace(tzinfo=timezone.utc)
        out.append(Bar(k, t, t + timedelta(hours=4), r.open, r.high, r.low, r.close))
    return out

def sim_bars(n, seed, start=8000.0):
    rng = np.random.default_rng(seed); t0 = datetime(2025, 5, 20, 12, tzinfo=timezone.utc)
    steps = rng.integers(0, 2, size=n * 14400, dtype=np.int8) * 2 - 1
    path = (start + 0.1 * np.cumsum(steps.astype(np.int64))).reshape(n, 14400)
    path = np.round(path, 1)
    return [Bar(k, t0 + timedelta(hours=4 * k), t0 + timedelta(hours=4 * (k + 1)), float(p[0]), float(p.max()), float(p.min()), float(p[-1]))
            for k, p in enumerate(path)]

def strategy(bars, tag):
    BD.load = lambda s, tf: bars
    BD.resample = lambda b, m: resample(b, 1440)   # UT haute = D1 (marché 24/7, agrégation UTC exacte)
    BD.COST["STEP"] = 0.1
    out = f"/tmp/step_{tag}.parquet"
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        BD.main("STEP", 2000, 2100, out)
    d = pd.read_parquet(out)
    return d

def persistence(bars):
    d1 = resample(bars, 1440); e = Engine(Config(enable_setups=False)); k = 0
    H = np.array([b.high for b in bars]); L = np.array([b.low for b in bars]); C = np.array([b.close for b in bars]); res = []
    for b in bars:
        i = b.index
        while k < len(d1) and d1[k].t_close <= b.t_close: e.on_bar(d1[k]); e.log.clear(); k += 1
        if k < 30: continue
        d = e.structure.trend
        if d == 0: continue
        a = e.ctx.atr[-1]; up = C[i] + d * a; dn = C[i] - d * a
        for j in range(i + 1, min(len(bars), i + 31)):
            hu = (H[j] >= up) if d == 1 else (L[j] <= up); hd = (L[j] <= dn) if d == 1 else (H[j] >= dn)
            if hu and hd: break
            if hu: res.append(1); break
            if hd: res.append(0); break
    return np.mean(res) if res else np.nan, len(res)

def summary(d):
    return {"n": len(d), "mfe1": (d.mfe_R >= 1).mean(), "mfe2": (d.mfe_R >= 2).mean(), "tp2": (d.r2 >= 2).mean(),
            "brut2": d.r2.mean(), "brut3": d.r3.mean()}

if __name__ == "__main__":
    rb = real_bars()
    rs = summary(strategy(rb, "real")); rp = persistence(rb)
    print("RÉEL   :", {k: round(v, 3) for k, v in rs.items()}, "| persistance D1 %.3f (n=%d)" % rp)
    sims = []
    for s in range(int(sys.argv[1]) if len(sys.argv) > 1 else 100):
        sb = sim_bars(len(rb), s)
        x = summary(strategy(sb, "sim")); x["pers"] = persistence(sb)[0]; sims.append(x)
    S = pd.DataFrame(sims)
    print("SIMULÉ : moyenne", S.mean().round(3).to_dict())
    print("         bande 5-95 %", {c: (round(S[c].quantile(.05), 3), round(S[c].quantile(.95), 3)) for c in S.columns})
    for c, v in list(rs.items())[1:]:
        print(f"   {c}: réel {v:.3f} -> rang parmi les simulations {(S[c] < v).mean():.2f}")
    print(f"   persistance: réel {rp[0]:.3f} -> rang {(S.pers < rp[0]).mean():.2f}")
