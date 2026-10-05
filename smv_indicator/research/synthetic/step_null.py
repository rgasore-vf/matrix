"""Step Index (Deriv) : marche aléatoire de ±0,1 par tick, 1 tick par seconde, 50/50 (définition Deriv,
vérifiée sur 3 000 bougies H4 réelles du compte : écart-type H4 11,96 contre 12,0 théorique,
autocorrélation -0,02). On simule 3 ans de M15 et on applique les MÊMES outils que sur l'EURUSD :
  1. persistance de la tendance H4 (course ±1 ATR H4 sur 24 h) ;
  2. étude des entrées M15 dans le sens H4 (research/daystudy/build_day.py).
Une marche aléatoire n'a pas de mémoire : toute règle d'entrée et de sortie y a une espérance nulle
avant coûts (théorème d'arrêt des martingales). C'est donc un témoin : ce que donne la stratégie quand
il n'y a RIEN à trouver."""
import os, sys
from datetime import datetime, timedelta, timezone
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..")); sys.path.insert(0, os.path.join(HERE, "..", "..")); sys.path.insert(0, os.path.join(HERE, "..", "daystudy"))
from smv.types import Bar
import build_day as BD

def simulate(years=3, seed=7, start=8000.0):
    rng = np.random.default_rng(seed)
    n = int(years * 365 * 96); bars = []; p = start; t0 = datetime(2023, 1, 2, tzinfo=timezone.utc)
    for c0 in range(0, n, 5000):
        m = min(5000, n - c0)
        steps = rng.integers(0, 2, size=(m, 900), dtype=np.int8) * 2 - 1
        path = (p + 0.1 * np.cumsum(steps.ravel().astype(np.int64))).reshape(m, 900)   # chemin continu d'une bougie à l'autre
        for k in range(m):
            row = np.round(path[k], 1); o = row[0]
            t = t0 + timedelta(minutes=15 * (c0 + k))
            bars.append(Bar(c0 + k, t, t + timedelta(minutes=15), float(o), float(row.max()), float(row.min()), float(row[-1])))
            p = row[-1]
    return bars

if __name__ == "__main__":
    bars = simulate()
    BD.load = lambda sym, tf: bars
    BD.COST["STEP"] = 0.1          # un pas d'écart (hypothèse ; écart réel non journalisé)
    out = sys.argv[1]
    BD.main("STEP", 2023, 2025, out)
