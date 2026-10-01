"""Chargement CSV et générateur de séries synthétiques (tests, démonstration)."""
from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta, timezone

from .types import Bar


def _parse_time(s: str) -> datetime:
    s = s.strip()
    if s.isdigit():
        v = int(s)
        if v > 10**11:  # millisecondes
            v //= 1000
        return datetime.fromtimestamp(v, tz=timezone.utc)
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def load_csv(path: str, timeframe_minutes: int) -> list[Bar]:
    """CSV avec en-tête : time, open, high, low, close[, volume]. Temps = ouverture de bougie,
    ISO 8601 ou epoch ; sans fuseau, UTC est supposé."""
    step = timedelta(minutes=timeframe_minutes)
    bars: list[Bar] = []
    with open(path, newline="") as f:
        rd = csv.DictReader(f)
        cols = {c.lower().strip(): c for c in rd.fieldnames or []}
        tcol = cols.get("time") or cols.get("datetime") or cols.get("date") or cols.get("timestamp")
        if tcol is None:
            raise ValueError("colonne de temps introuvable (time, datetime, date, timestamp)")
        for row in rd:
            t = _parse_time(row[tcol])
            vol = float(row[cols["volume"]]) if "volume" in cols and row[cols["volume"]] else 0.0
            bars.append(Bar(len(bars), t, t + step, float(row[cols["open"]]), float(row[cols["high"]]),
                            float(row[cols["low"]]), float(row[cols["close"]]), vol))
    return bars


def synthetic(n: int, seed: int = 0, start: float = 1.1000, vol: float = 0.0008,
              timeframe_minutes: int = 15, t0: datetime | None = None) -> list[Bar]:
    """Marche aléatoire à régimes (tendance, range) ; reproductible par `seed`."""
    rng = random.Random(seed)
    t = t0 or datetime(2025, 1, 6, 0, 0, tzinfo=timezone.utc)
    step = timedelta(minutes=timeframe_minutes)
    bars: list[Bar] = []
    price = start
    drift = 0.0
    for i in range(n):
        if i % rng.randint(40, 120) == 0:
            drift = rng.choice([-1, 0, 0, 1]) * vol * rng.uniform(0.1, 0.4)
        o = price
        c = o + drift + rng.gauss(0, vol)
        h = max(o, c) + abs(rng.gauss(0, vol * 0.6))
        lo = min(o, c) - abs(rng.gauss(0, vol * 0.6))
        r = 5
        bars.append(Bar(i, t, t + step, round(o, r), round(h, r), round(lo, r), round(c, r)))
        price = c
        t += step
    return bars


def from_ohlc(rows: list[tuple[float, float, float, float]], timeframe_minutes: int = 15,
              t0: datetime | None = None) -> list[Bar]:
    """Construit des bougies à partir de tuples (open, high, low, close)."""
    t = t0 or datetime(2025, 1, 6, 0, 0, tzinfo=timezone.utc)
    step = timedelta(minutes=timeframe_minutes)
    out = []
    for i, (o, h, lo, c) in enumerate(rows):
        out.append(Bar(i, t, t + step, o, h, lo, c))
        t += step
    return out


def from_closes(points: list[float], wick: float = 0.0, timeframe_minutes: int = 15) -> list[Bar]:
    """Bougies dont l'ouverture est la clôture précédente ; mèches de taille `wick`.

    Pratique pour décrire une structure par une suite de prix de clôture."""
    rows = []
    prev = points[0]
    for c in points:
        o = prev
        rows.append((o, max(o, c) + wick, min(o, c) - wick, c))
        prev = c
    return from_ohlc(rows, timeframe_minutes)
