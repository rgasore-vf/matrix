"""Test séparé de chaque concept de la stratégie (Modules 1 à 9), sur données réelles et mélangées.

A. Signaux directionnels. Pour chaque événement confirmé à la clôture de la bougie i, on
   « entre » à close[i] dans le sens que le dépôt attribue au concept, puis on mesure une course
   symétrique : le prix atteint-il +k ATR avant -k ATR (k = 1 et 2), dans les 300 bougies ?
   Sous l'hypothèse « le concept n'apporte rien », le taux de réussite est voisin de 50 %.
   Si les deux bornes sont touchées dans la même bougie, l'issue compte pour 0,5.
   Aucun coût : on teste l'idée, pas une exécution.

B. Affirmations sur la liquidité. Taux de prise d'un niveau dans les H bougies, par tranche de
   distance (en ATR) au moment où le niveau est connu, comparé à des pivots ordinaires.

C. Cause et effet. Corrélation de rang entre la durée d'une consolidation et l'amplitude du
   mouvement qui suit sa sortie (50 bougies, en ATR).

Usage : python research/modules.py SYMBOL TF [shuffle_seed] > fichier.json
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from marketdata import load  # noqa: E402
from smv import Config, Engine  # noqa: E402
from study_nulls import shuffled  # noqa: E402

HORIZON = 300
LIQ_H = 200


def race(bars, atr, i, d, k):
    e = bars[i].close
    a = atr[i]
    if a <= 0:
        return None
    up, dn = e + k * a, e - k * a
    for j in range(i + 1, min(len(bars), i + 1 + HORIZON)):
        b = bars[j]
        hu, hd = b.high >= up, b.low <= dn
        if hu and hd:
            return 0.5
        if hu:
            return 1.0 if d > 0 else 0.0
        if hd:
            return 0.0 if d > 0 else 1.0
    return None


def signals(log, eng):
    """(nom du test, bougie, sens) : sens = ce que le dépôt fait attendre du concept."""
    zones = {}
    first_touch = set()
    trend_at = {}
    out = []
    for e in log:
        k, i, d = e.kind, e.confirm_index, e.direction
        if k == "BOS_CHANGE":
            out.append(("M1 BOS changement (suivre)", i, d))
        elif k == "BOS_CONTINUATION":
            out.append(("M1 BOS continuation (suivre)", i, d))
        elif k == "TREND_INIT":
            out.append(("M1 init tendance (suivre)", i, d))
        elif k == "FAIL":
            out.append(("M4 fail = changement de caractère (retournement)", i, d))
        elif k == "PROTECTED_SWEEP":
            # mèche sous le protégé sans clôture : prise de liquidité, la tendance reprend
            out.append(("M1/M5 prise du niveau protégé (reprise tendance)", i, -d))
        elif k == "LIQ_CLEAN":
            out.append(("M5 liquidité prise en mèche (retournement)", i, -d))
        elif k == "LIQ_BOS":
            out.append(("M4 intact cassé en clôture (continuation)", i, d))
        elif k == "ZONE":
            zones[e.ref] = e.data
        elif k == "ZONE_TOUCH" and e.data["zone"] not in first_touch:
            first_touch.add(e.data["zone"])
            z = zones.get(e.data["zone"])
            if z is None:
                continue
            src = z["source"]
            name = {"BOS_CHANGE": "M3 1re touche zone décisionnelle (BOS chgt)",
                    "BOS_CONTINUATION": "M3 1re touche zone de continuation",
                    "PIVOT": "M3 1re touche zone sans BOS"}.get(src)
            if name:
                out.append((name, i, d))
            if src != "PIVOT":
                out.append(("M2 zone avec BM" if z["bm_index"] is not None else "M2 zone sans BM", i, d))
                out.append(("M2 zone avec doji signature" if z["doji_signature"] else "M2 zone sans doji signature", i, d))
        elif k == "ODF_LINK" and e.data["is_odf"]:
            out.append(("M3 order flow (nouvelle zone liée)", i, d))
        elif k == "BREAKER":
            out.append(("M3 breaker créé (polarité inversée)", i, d))
        elif k == "BREAKER_REACTION":
            out.append(("M3 réaction sur breaker", i, d))
        elif k == "RANGE_SWEEP":
            lab = e.data["label_candidate"].split("+")[0]
            # STB/SPRING (prise basse en accumulation) -> achat ; UT/UTAD -> vente ; UA, MSO : idem retournement
            out.append((f"M7 prise de borne {lab} (retournement)", i, -d))
        elif k == "RANGE_EXIT":
            tag = "confirmée" if e.data["outcome"] == "confirmed" else "infirmée"
            out.append((f"M4 sortie de cause {tag} (suivre la sortie)", i, d))
        elif k == "CAUSE_COMPLETE":
            out.append(("M4 cause complète (sens de l'intention)", i, d))
        elif k == "IMBALANCE":
            out.append(("M7 imbalance / FVG (sens du déséquilibre)", i, d))
        elif k == "LIQ_SIGNATURE":
            out.append(("M2 signature de liquidité (vers la mèche)", i, d))
        elif k == "SETUP_TRIGGERED":
            out.append((f"M7/M9 setup {e.data['type']} déclenché", i, d))
    return out


def liquidity_claims(bars, atr, log):
    taken = {}
    for e in log:
        if e.kind in ("LIQ_CLEAN", "LIQ_BOS"):
            taken[e.data["level"]] = e.confirm_index
    groups = defaultdict(lambda: [0, 0])

    def add(kind, ref, price, c):
        dist = abs(bars[c].close - price) / atr[c] if atr[c] > 0 else None
        if dist is None or c + LIQ_H >= len(bars):
            return
        t = taken.get(ref)
        if t is not None and t <= c:
            return
        b = "d<1" if dist < 1 else "d1-3" if dist < 3 else "d>=3"
        g = groups[f"{kind}|{b}"]
        g[0] += int(t is not None and t - c <= LIQ_H)
        g[1] += 1

    eq_seen = set()
    for e in log:
        if e.kind == "LIQ_LEVEL":
            add("pivot ordinaire" if e.data["source"] == "PIVOT" else "M2 signature de liquidité",
                e.ref, e.price, e.confirm_index)
        elif e.kind == "EQUAL_LEVELS" and e.data["second"] not in eq_seen:
            eq_seen.add(e.data["second"])
            add("M5 EQH/EQL", e.data["second"], e.price, e.confirm_index)
        elif e.kind == "INDUCEMENT":
            add("M5 inducement", e.data["level_ref"], e.price, e.confirm_index)
    return {k: {"n": n, "taken": round(s / n, 4)} for k, (s, n) in groups.items() if n}


def cause_effect(bars, atr, log):
    pts = []
    for e in log:
        if e.kind == "RANGE_EXIT":
            i = e.confirm_index
            if i + 50 >= len(bars) or atr[i] <= 0:
                continue
            seg = bars[i + 1:i + 51]
            move = (max(b.high for b in seg) - bars[i].close) if e.direction > 0 else (bars[i].close - min(b.low for b in seg))
            pts.append((e.data["duration"], move / atr[i]))
    if len(pts) < 10:
        return {"n": len(pts)}
    def ranks(v):
        o = sorted(range(len(v)), key=lambda k: v[k]); r = [0] * len(v)
        for pos, k in enumerate(o):
            r[k] = pos
        return r
    x = ranks([p[0] for p in pts]); y = ranks([p[1] for p in pts]); n = len(pts)
    mx, my = sum(x) / n, sum(y) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(x, y))
    vx = sum((a - mx) ** 2 for a in x) ** 0.5; vy = sum((b - my) ** 2 for b in y) ** 0.5
    q = sorted(pts)
    third = n // 3
    return {"n": n, "spearman": round(cov / (vx * vy), 4),
            "effect_short_causes": round(sum(p[1] for p in q[:third]) / third, 3),
            "effect_long_causes": round(sum(p[1] for p in q[-third:]) / third, 3)}


def main():
    sym, tf = sys.argv[1], sys.argv[2]
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else None
    bars = load(sym, tf)
    if seed is not None:
        bars = shuffled(bars, seed)
    eng = Engine(Config(enable_imbalance=True, zones_on="all_pivots"))
    log = eng.run(bars)
    atr = eng.ctx.atr
    res = defaultdict(lambda: {"n1": 0, "w1": 0.0, "n2": 0, "w2": 0.0})
    for name, i, d in signals(log, eng):
        if d == 0:
            continue
        for k, nk, wk in ((1, "n1", "w1"), (2, "n2", "w2")):
            r = race(bars, atr, i, d, k)
            if r is not None:
                res[name][nk] += 1
                res[name][wk] += r
    print(json.dumps({"symbol": sym, "tf": tf, "series": "real" if seed is None else f"shuffled{seed}",
                      "signals": res, "liquidity": liquidity_claims(bars, atr, log),
                      "cause_effect": cause_effect(bars, atr, log)}))


if __name__ == "__main__":
    main()
