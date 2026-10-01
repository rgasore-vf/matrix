"""Validation du portage MQL5 : compare le journal exporté par SMV_Indicator (MT5) avec le
journal du moteur Python calculé sur EXACTEMENT les mêmes bougies.

Usage :
    python tools/mt5_parity.py <chemin>/EURUSD_M15        # lit _bars.tsv et _events.tsv
    python tools/mt5_parity.py <chemin>/EURUSD_M15 --write-reference
        # écrit aussi <chemin>/EURUSD_M15_python.tsv au format MT5 (pour un diff texte)

Format (écrit par SMV_Indicator.mq5, fonction Export) :
- _bars.tsv   : index, t_open_utc (epoch), t_close_utc, t_srv, open, high, low, close ;
- _events.tsv : lignes « # » d'en-tête (dont « #config clé=valeur;... »), puis
                kind, confirm, anchor, dir, price, ref, data (« clé=valeur;... »).

Comparaison : ordre, type, indices, direction, ref à l'identique ; prix et données numériques
à 1e-9 près en relatif, sauf les champs arrondis (r, mfe_r, rr, risk_atr) comparés à
l'arrondi près (Python round() et MQL5 NormalizeDouble peuvent différer sur une égalité).
Code de sortie 0 si les journaux sont identiques, 1 sinon.
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import fields
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from smv import Bar, Config, Engine  # noqa: E402
from smv.types import Event  # noqa: E402

ROUNDED_TOL = {"r": 1e-4, "mfe_r": 1e-4, "rr": 1e-2, "risk_atr": 1e-3}


# -- lecture ------------------------------------------------------------------------
def read_bars(path: str) -> list[Bar]:
    out: list[Bar] = []
    with open(path, encoding="utf-8", errors="replace") as f:
        next(f)
        for line in f:
            p = line.rstrip("\n").split("\t")
            if len(p) < 8:
                continue
            t0 = datetime.fromtimestamp(int(p[1]), tz=timezone.utc)
            t1 = datetime.fromtimestamp(int(p[2]), tz=timezone.utc)
            out.append(Bar(int(p[0]), t0, t1, float(p[4]), float(p[5]), float(p[6]), float(p[7])))
    return out


def parse_kv(s: str) -> dict[str, str]:
    out: dict[str, str] = {}
    if not s:
        return out
    for part in s.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k] = v
    return out


def config_from_header(kv: dict[str, str]) -> Config:
    types = {f.name: f.type for f in fields(Config)}
    args = {}
    for k, v in kv.items():
        if k not in types:
            continue
        t = str(types[k])
        if v == "":
            args[k] = None
        elif "bool" in t:
            args[k] = v == "true"
        elif t.startswith("int"):
            args[k] = int(v)
        elif "float" in t:
            args[k] = float(v)
        else:
            args[k] = v
    return Config(**args)


def read_events(path: str) -> tuple[dict[str, str], list[tuple]]:
    header: dict[str, str] = {}
    rows = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("#config "):
                header = parse_kv(line[len("#config "):])
                continue
            if line.startswith("#") or line.startswith("kind\t") or not line:
                continue
            p = line.split("\t")
            while len(p) < 7:
                p.append("")
            rows.append((p[0], int(p[1]), int(p[2]), int(p[3]), float(p[4]), p[5], parse_kv(p[6])))
    return header, rows


# -- normalisation ------------------------------------------------------------------
def fmt_value(v) -> str:
    """Valeur Python -> texte au format MT5 (pour --write-reference)."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return f"{v:.15g}"
    if isinstance(v, (list, tuple)):
        return "|".join(fmt_value(x) for x in v)
    return str(v)


def same_value(key: str, py, mt: str) -> bool:
    if py is None or py == [] or py == ():
        return mt == ""
    if isinstance(py, bool):
        return mt == ("true" if py else "false")
    if isinstance(py, (list, tuple)):
        parts = mt.split("|") if mt else []
        return len(parts) == len(py) and all(same_value(key, a, b) for a, b in zip(py, parts))
    if isinstance(py, (int, float)):
        try:
            m = float(mt)
        except ValueError:
            return False
        tol = ROUNDED_TOL.get(key)
        if tol is not None:
            return abs(m - py) <= tol * 0.51 + 1e-12
        return abs(m - py) <= 1e-9 * max(1.0, abs(py))
    return str(py) == mt


def compare(py_log: list[Event], mt_rows: list[tuple], max_report: int = 20) -> list[str]:
    errs: list[str] = []
    n = min(len(py_log), len(mt_rows))
    for k in range(n):
        e = py_log[k]
        kind, confirm, anchor, d, price, ref, data = mt_rows[k]
        head = (e.kind, e.confirm_index, e.anchor_index, e.direction, e.ref)
        if head != (kind, confirm, anchor, d, ref) or abs(e.price - price) > 1e-9 * max(1.0, abs(e.price)):
            errs.append(f"#{k}: python={head + (e.price,)} mt5={(kind, confirm, anchor, d, ref, price)}")
        else:
            keys = set(e.data) | set(data)
            for key in sorted(keys):
                if key not in e.data or key not in data or not same_value(key, e.data[key], data[key]):
                    errs.append(f"#{k} {e.kind} {e.ref} [{key}]: python={e.data.get(key)!r} mt5={data.get(key)!r}")
        if len(errs) >= max_report:
            return errs
    if len(py_log) != len(mt_rows):
        errs.append(f"nombre d'événements : python={len(py_log)} mt5={len(mt_rows)}")
    return errs


def write_reference(path: str, log: list[Event]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write("kind\tconfirm\tanchor\tdir\tprice\tref\tdata\n")
        for e in log:
            data = ";".join(f"{k}={fmt_value(v)}" for k, v in e.data.items())
            f.write(f"{e.kind}\t{e.confirm_index}\t{e.anchor_index}\t{e.direction}\t{e.price:.15g}\t{e.ref}\t{data}\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("base", help="préfixe des fichiers exportés, ex. .../MQL5/Files/SMV/EURUSD_M15")
    ap.add_argument("--write-reference", action="store_true")
    ap.add_argument("--max-report", type=int, default=20)
    a = ap.parse_args(argv)
    bars = read_bars(a.base + "_bars.tsv")
    header, rows = read_events(a.base + "_events.tsv")
    cfg = config_from_header(header)
    log = Engine(cfg).run(bars)
    if a.write_reference:
        write_reference(a.base + "_python.tsv", log)
    errs = compare(log, rows, a.max_report)
    print(f"bougies : {len(bars)} ; événements python : {len(log)} ; mt5 : {len(rows)}")
    if not errs:
        print("PARITÉ : journaux identiques")
        return 0
    print("DIVERGENCES (les premières) :")
    for e in errs:
        print("  " + e)
    return 1


if __name__ == "__main__":
    sys.exit(main())
