"""Volatilité par créneau de 15 min en heure de Paris, séparément hiver / été / semaines désynchronisées.

Usage : python research/study_sessions.py > research/results_sessions.json
"""
import json
import os
import statistics as st
import sys
from collections import defaultdict
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(__file__))
from marketdata import load  # noqa: E402

P = ZoneInfo("Europe/Paris")
NY = ZoneInfo("America/New_York")


def main():
    out = {}
    for sym in ("EURUSD", "XAUUSD"):
        b = load(sym, "m15", "2015-01-01", "2022-01-01")
        acc = defaultdict(lambda: defaultdict(list))
        for x in b:
            lp, ln = x.t_open.astimezone(P), x.t_open.astimezone(NY)
            eu, us = bool(lp.dst()), bool(ln.dst())
            season = "summer" if eu and us else "winter" if not (eu or us) else "mismatch"
            acc[season][f"{lp.hour:02d}:{lp.minute:02d}"].append(x.high - x.low)
        r = {}
        for season, d in acc.items():
            means = {k: st.mean(v) for k, v in d.items()}
            m = st.mean(means.values())
            hourly = {}
            for h in range(24):
                vals = [means[f"{h:02d}:{mm:02d}"] for mm in (0, 15, 30, 45) if f"{h:02d}:{mm:02d}" in means]
                if vals:
                    hourly[h] = round(st.mean(vals) / m, 2)
            top = sorted(means, key=lambda k: -means[k])[:8]
            r[season] = {"bars": sum(len(v) for v in d.values()), "top_slots": top, "hourly_rel": hourly}
        out[sym] = r
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
