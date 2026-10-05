"""Classe chaque trade perdant (stop avant +1 R) par cause probable, et trace des journées."""
import os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..")); sys.path.insert(0, os.path.join(HERE, "..", ".."))
from marketdata import load
from smv import Config, Engine
from smv.mtf import resample

def h4_changes(sym):
    bars = load(sym, "m15"); h4 = resample(bars, 240)
    eng = Engine(Config(zones_on="bos_origin", enable_setups=False)); out = []
    for b in h4:
        for e in eng.on_bar(b):
            if e.kind == "BOS_CHANGE": out.append((b.t_close.timestamp(), e.direction))
        eng.log.clear()
    return bars, h4, out

def classify(d, bars, changes):
    ct = np.array([c[0] for c in changes]); cd = np.array([c[1] for c in changes])
    modes = []
    for r in d.itertuples():
        if r.mfe_R >= 1 or not r.stopped:
            modes.append("gagnant ou neutre (>= +1 R ou pas stoppé)"); continue
        t_fill = r.fill_t; t_exit = bars[r.exit_i].t_open.timestamp()
        m = (ct > t_fill) & (ct <= t_exit + 900) & (cd == -r.d)
        dur = r.exit_i - r.fill_i
        if r.risk_pips <= 5 and dur <= 4:
            modes.append("A stop trop serré (<= 5 pips, touché en <= 1 h)")
        elif m.any():
            modes.append("B la tendance H4 s'est retournée pendant le trade")
        elif (r.h4_pos > 0.75) or (r.h4_bos_n >= 3):
            modes.append("C entrée en fin de mouvement H4 (haut de jambe ou 3e BOS H4+)")
        elif r.room_liq_R < 1:
            modes.append("D pas de place : liquidité H4 à moins de 1 R")
        else:
            modes.append("E retour normal contre l'entrée (bruit)")
    d = d.copy(); d["mode"] = modes
    return d

if __name__ == "__main__":
    d = pd.read_parquet(sys.argv[1]); sym = d.symbol.iloc[0]
    bars, h4, ch = h4_changes(sym)
    d = classify(d, bars, ch)
    d.to_parquet(sys.argv[2])
    t = d["mode"].value_counts()
    print((t / len(d)).round(3).to_string()); print("n", len(d))
