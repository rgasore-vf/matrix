"""Trace des journées M15 avec le biais H4, les entrées, stops, TP 2 R et la cause de chaque perte."""
import os, sys
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from zoneinfo import ZoneInfo
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..")); sys.path.insert(0, os.path.join(HERE, "..", ".."))
from marketdata import load
PARIS = ZoneInfo("Europe/Paris")
GREEN, ORANGE, BLUE, GREY, INK = "#788C5D", "#D97757", "#6A9BCC", "#B0AEA5", "#141413"

def plot_day(bars, d, date, out):
    day = d[d.date == date]
    idx = [b.index for b in bars if b.t_open.astimezone(PARIS).date().isoformat() == date]
    if not idx: return
    i0, i1 = max(0, idx[0] - 32), min(len(bars) - 1, idx[-1] + 24)
    seg = bars[i0:i1 + 1]
    fig, ax = plt.subplots(figsize=(14, 6.5), dpi=110)
    fig.patch.set_facecolor("#FAF9F5"); ax.set_facecolor("#FAF9F5")
    for k, b in enumerate(seg):
        c = GREEN if b.close >= b.open else ORANGE
        ax.plot([k, k], [b.low, b.high], color=c, lw=0.8)
        ax.add_patch(plt.Rectangle((k - 0.35, min(b.open, b.close)), 0.7, max(abs(b.close - b.open), 1e-6), color=c))
    ax.axvspan(idx[0] - i0 - 0.5, idx[-1] - i0 + 0.5, color="#F0EEE6", zorder=-1)
    for r in day.itertuples():
        x0 = r.fill_i - i0; x1 = min(r.exit_i, i1) - i0; xs = r.sig_i - i0
        risk = abs(r.E - r.S); tp = r.E + r.d * 2 * risk
        win = r.r2 >= 2
        col = GREEN if win else (GREY if not r.stopped else ORANGE)
        ax.hlines(r.E, xs, x1, color=INK, lw=1); ax.hlines(r.S, xs, x1, color=ORANGE, lw=1, ls="--")
        ax.hlines(tp, xs, x1, color=GREEN, lw=1, ls=":")
        ax.scatter([x0], [r.E], marker="^" if r.d == 1 else "v", s=90, color=col, zorder=5, edgecolor=INK)
        lab = ("TP2" if win else ("stop" if r.stopped else "horizon")) + f" | MFE {r.mfe_R:.1f}R | stop {r.risk_pips:.1f}p"
        lab += f"\nH4 pos {r.h4_pos:.2f}, BOS H4 n°{r.h4_bos_n}, BOS M15 n°{r.m15_bos_n}"
        if not win: lab += "\n" + r.mode.split(" (")[0]
        ax.annotate(lab, (x0, r.E), xytext=(8, -38 if r.d == 1 else 18), textcoords="offset points", fontsize=7.5, color=INK,
                    bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=col, lw=0.8))
    ticks = list(range(0, len(seg), 8))
    ax.set_xticks(ticks); ax.set_xticklabels([seg[k].t_open.astimezone(PARIS).strftime("%d %H:%M") for k in ticks], fontsize=8, rotation=0)
    bias = "HAUSSIER" if day.d.iloc[0] == 1 else "BAISSIER"
    ax.set_title(f"EURUSD M15, {date} (heure de Paris), biais H4 {bias} : {len(day)} entrées, {int((day.r2>=2).sum())} à TP 2R", fontsize=12, color=INK, loc="left")
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.grid(axis="y", color="#E8E6DC", lw=0.6)
    fig.tight_layout(); fig.savefig(out); plt.close(fig)

if __name__ == "__main__":
    d = pd.read_parquet(sys.argv[1]); outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)
    bars = load(d.symbol.iloc[0], "m15")
    for date in sys.argv[3:]:
        plot_day(bars, d, date, os.path.join(outdir, f"{date}.png"))
