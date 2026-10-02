"""Rejeu incrémental des candidats figés A, B, C, avec la MÊME logique que l'EA MT5
(mt5/Experts/ASYM/ASYM_Vault.mq5) : bougie close par bougie close, shadow mis à jour à
chaque bougie, sortie à l'horizon.

Deux usages :
  1. Contrôle de l'EA contre la recherche (données de recherche) :
       python research/asym/vault_replay.py check B EURUSD
     compare chaque trade du rejeu aux colonnes r_atr_* de build_matrix2 (doivent être identiques).
  2. Parité avec un journal MT5 (bougies exportées par l'EA) :
       python research/asym/vault_replay.py parity B chemin/..._bars.csv chemin/..._shadow.csv
     recalcule les signaux et les R à partir des bougies de l'EA et les compare à son shadow.
"""
from __future__ import annotations

import csv
import os
import sys
from datetime import datetime, timedelta, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", ".."))

from smv import Config, Engine  # noqa: E402
from smv.types import Bar  # noqa: E402

TPS = (1.0, 1.5, 2.0, 2.5, 3.0, 4.0)
STRAT = {"A": ("h4", 96, 600, 2.0), "B": ("h4", 96, 600, 3.0), "C": ("d1", 20, 120, 3.0)}


class Shadow:
    def __init__(self, sig, d, atr):
        self.sig, self.d, self.atr = sig, d, atr
        self.E = None
        self.stopped, self.t_sl, self.sl_r = False, None, -1.0
        self.r = [None] * len(TPS)
        self.mfe, self.mae, self.done = -np.inf, -np.inf, False

    def update(self, j, b, H):
        rel = j - (self.sig + 1)
        if rel < 0 or self.done:
            return
        d, risk = self.d, self.atr
        if rel == 0:
            self.E = b.open
        E = self.E
        fav = ((b.high - E) if d == 1 else (E - b.low)) / risk
        adv = ((E - b.low) if d == 1 else (b.high - E)) / risk
        if not self.stopped:
            self.mfe = max(self.mfe, fav)
            if adv >= 1.0:
                self.stopped, self.t_sl = True, rel
                gap = (((E - b.open) if d == 1 else (b.open - E)) / risk) if rel > 0 else 0.0
                self.sl_r = -max(1.0, gap)
            else:
                for k, tp in enumerate(TPS):
                    if self.r[k] is None and fav >= tp:
                        self.r[k] = tp
        self.mae = max(self.mae, adv)
        if rel == H - 1:
            for k in range(len(TPS)):
                if self.r[k] is None:
                    self.r[k] = self.sl_r if self.stopped else (b.close - E) * d / risk
            self.done = True


def replay(bars, strat, start_index=0):
    """Renvoie la liste des shadows terminés (signaux à partir de start_index)."""
    tf, H, warm, _ = STRAT[strat]
    eng = Engine(Config(zones_on="bos_origin"))
    sh = []
    for b in bars:
        i = b.index
        evs = eng.on_bar(b)
        eng.log.clear()
        for s in sh:
            s.update(i, b, H)
        if i < warm or i < start_index:
            continue
        atr = eng.ctx.atr[i]
        if atr <= 0:
            continue
        want = set()
        if tf == "h4":
            lo_i = i - 20
            hi = max(x.high for x in bars[lo_i:i]); lo = min(x.low for x in bars[lo_i:i])
            comp = (hi - lo) / atr
            if comp <= 4.0 and (b.high - b.low) >= 1.5 * atr and b.close != b.open and (b.high - b.low) / atr >= 2.0:
                want.add(1 if b.close > b.open else -1)
        else:
            for e in evs:
                if e.kind in ("BOS_CONTINUATION", "BOS_CHANGE") and e.direction in (1, -1):
                    want.add(-e.direction)
        for d in sorted(want, reverse=True):
            sh.append(Shadow(i, d, atr))
    return [s for s in sh if s.done]


def check(strat, symbol):
    import pandas as pd
    from marketdata import load
    tf, H, warm, tp = STRAT[strat]
    bars = load(symbol, tf)
    res = replay(bars, strat)
    df = pd.read_parquet(f"/tmp/am_{tf}/{symbol}.parquet")
    df = df[(df.f_volx == 1) & (df.range_atr >= 2)] if tf == "h4" else df[df.f_bos_fade == 1]
    ref = {(int(r["i"]), int(r["d"])): r for r in df.to_dict("records")}
    mine = {(s.sig, s.d): s for s in res}
    common = set(ref) & set(mine)
    bad = 0
    for key in common:
        row = ref[key]
        for k, t in enumerate(TPS):
            if abs(float(row[f"r_atr_{t:g}"]) - mine[key].r[k]) > 1e-3:
                bad += 1
                if bad <= 5:
                    print("écart", key, t, float(row[f"r_atr_{t:g}"]), mine[key].r[k])
        if abs(float(row["mfe_atr"]) - mine[key].mfe) > 1e-3:
            bad += 1
    only_ref, only_mine = set(ref) - set(mine), set(mine) - set(ref)
    print(f"{strat} {symbol}: recherche {len(ref)}, rejeu {len(mine)}, communs {len(common)}, "
          f"seulement recherche {len(only_ref)}, seulement rejeu {len(only_mine)}, écarts de R {bad}")
    return bad == 0 and not only_ref


def read_ea_bars(path, tf):
    step = timedelta(hours=4) if tf == "h4" else timedelta(days=1)
    bars, live_from = [], None
    with open(path) as f:
        for r in csv.DictReader(f):
            t = datetime.strptime(r["time_srv"], "%Y.%m.%d %H:%M").replace(tzinfo=timezone.utc)
            b = Bar(len(bars), t, t + step, float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]))
            if live_from is None and r["live"] == "1":
                live_from = b.index
            bars.append(b)
    return bars, live_from


def parity(strat, bars_csv, shadow_csv):
    tf = STRAT[strat][0]
    bars, live_from = read_ea_bars(bars_csv, tf)
    res = replay(bars, strat, live_from or 0)
    by_time = {(bars[s.sig].t_open.strftime("%Y.%m.%d %H:%M"), s.d): s for s in res}
    ea = {}
    with open(shadow_csv) as f:
        for r in csv.DictReader(f):
            ea[(r["sig_time_srv"], int(r["dir"]))] = r
    common = set(ea) & set(by_time)
    bad = 0
    for key in common:
        for k, t in enumerate(TPS):
            if abs(float(ea[key][f"r_{t:g}"]) - by_time[key].r[k]) > 2e-3:
                bad += 1
                if bad <= 10:
                    print("écart", key, t, ea[key][f"r_{t:g}"], round(by_time[key].r[k], 4))
    print(f"EA {len(ea)}, rejeu {len(by_time)}, communs {len(common)}, seulement EA {len(set(ea) - set(by_time))}, "
          f"seulement rejeu {len(set(by_time) - set(ea))}, écarts {bad}")
    print("Remarque : un signal au début de la période peut différer si l'ATR ou la structure n'avaient pas convergé.")


if __name__ == "__main__":
    if sys.argv[1] == "check":
        ok = all(check(sys.argv[2], s) for s in sys.argv[3:])
        print("PARITÉ RECHERCHE : OK" if ok else "PARITÉ RECHERCHE : ÉCARTS")
    elif sys.argv[1] == "parity":
        parity(sys.argv[2], sys.argv[3], sys.argv[4])
