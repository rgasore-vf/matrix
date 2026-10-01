"""Chargement des données réelles utilisées pour le calibrage (research/).

Source : dépôt public GitHub ejtraderLabs/historical-data (cloné hors du projet, non versionné).
- Prix stockés en entiers : EURUSD x 1e5, XAUUSD x 100.
- Horodatage : heure serveur de courtier EET/EEST (UTC+2 / UTC+3 selon les règles européennes,
  fuseau IANA Europe/Athens). Déduit : ouverture hebdomadaire le lundi 00:00 et clôture le
  vendredi 23:45, sauf pendant les semaines où les heures d'été américaine et européenne sont
  désynchronisées (clôture à 22:45, car 17:00 New York tombe alors à 23:00 EET). Une première
  hypothèse « New York + 7 h » décalait ces semaines d'une heure ; elle a été rejetée en
  comparant les pics de volatilité (ouverture de Londres, chiffres US de 8 h 30 ET).
"""
from __future__ import annotations

import csv
import os
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from smv.types import Bar  # noqa: E402

ROOT = os.environ.get("SMV_DATA", "/home/user/mktdata/ej")
SCALE = {"EURUSD": 1e5, "XAUUSD": 100.0}
TF_MIN = {"m15": 15, "m30": 30, "h1": 60, "h4": 240, "d1": 1440}
SERVER_TZ = ZoneInfo("Europe/Athens")


def server_to_utc(s: datetime) -> datetime:
    return s.replace(tzinfo=SERVER_TZ).astimezone(timezone.utc)


def load(symbol: str, tf: str, start: str | None = None, end: str | None = None) -> list[Bar]:
    path = os.path.join(ROOT, symbol, f"{symbol}{tf}.csv")
    sc = SCALE.get(symbol, 1e3 if symbol.endswith("JPY") else 1e5)
    step = timedelta(minutes=TF_MIN[tf])
    out: list[Bar] = []
    with open(path) as f:
        rd = csv.reader(f)
        next(rd)
        for r in rd:
            if start and r[0] < start:
                continue
            if end and r[0] >= end:
                break
            ts = datetime.fromisoformat(r[0])
            t = server_to_utc(ts) if tf != "d1" else ts.replace(tzinfo=timezone.utc)
            nd = 2 if symbol == "XAUUSD" else 3 if symbol.endswith("JPY") else 5
            o, h, l, c = (round(float(x) / sc, nd) for x in r[1:5])
            h = max(h, o, c)
            l = min(l, o, c)
            out.append(Bar(len(out), t, t + step, o, h, l, c, float(r[5])))
    return out


def pip(symbol: str) -> float:
    """Taille du « pip » telle qu'utilisée dans le dépôt : 0.0001 (EURUSD), 0.1 $ (or, M2/M6 :
    « pour le gold, il faut juste décaler la virgule »)."""
    return 0.0001 if symbol == "EURUSD" else 0.1
