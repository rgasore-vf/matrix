"""Exécute le moteur sur un CSV (ou une série synthétique) et écrit événements + graphique.

Exemples :
  python tools/run_smv.py --synthetic 1500 --seed 1 --out out/demo
  python tools/run_smv.py --csv eurusd_m15.csv --tf 15 --out out/eurusd --from 500 --to 900
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from dataclasses import asdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from render.svg import render  # noqa: E402
from smv import Config, Engine  # noqa: E402
from smv.data import load_csv, synthetic  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--csv")
    src.add_argument("--synthetic", type=int)
    ap.add_argument("--tf", type=int, default=15, help="UT en minutes")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", required=True, help="préfixe des fichiers de sortie")
    ap.add_argument("--from", dest="start", type=int, default=None)
    ap.add_argument("--to", dest="end", type=int, default=None)
    ap.add_argument("--mode", choices=["A", "B"], default="A")
    ap.add_argument("--pivot", type=int, default=2)
    ap.add_argument("--imbalance", action="store_true")
    ap.add_argument("--sessions", action="store_true")
    a = ap.parse_args()

    bars = load_csv(a.csv, a.tf) if a.csv else synthetic(a.synthetic, seed=a.seed, timeframe_minutes=a.tf)
    cfg = Config(major_mode=a.mode, pivot_left=a.pivot, pivot_right=a.pivot,
                 enable_imbalance=a.imbalance, enable_sessions=a.sessions)
    log = Engine(cfg).run(bars)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out + "_events.json", "w") as f:
        json.dump([{**asdict(e), "data": dict(e.data)} for e in log], f, indent=1, default=str)
    end = a.end if a.end is not None else len(bars) - 1
    start = a.start if a.start is not None else max(0, end - 300)
    svg = render(bars, log, start, end, title=f"SMV v0.1, lecture {a.mode}, bougies {start}-{end}")
    with open(a.out + "_chart.svg", "w") as f:
        f.write(svg)
    print(f"{len(bars)} bougies, {len(log)} événements")
    for k, v in Counter(e.kind for e in log).most_common():
        print(f"  {k:18s} {v}")
    print(f"écrit : {a.out}_events.json, {a.out}_chart.svg")


if __name__ == "__main__":
    main()
