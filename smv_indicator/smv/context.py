"""Historique des bougies closes et indicateurs causaux (ATR de Wilder).

Le contexte ne contient que des bougies closes. Toute lecture se fait sur des
indices <= dernier indice ajouté ; aucune fonction ne lit au-delà.
"""
from __future__ import annotations

from datetime import timezone
from math import isfinite

from .types import Bar


def validate_bar(bar: Bar) -> None:
    """Validate a closed interval before any state is changed (gaps are allowed)."""
    for name in ("open", "high", "low", "close", "volume"):
        v = getattr(bar, name)
        if not isinstance(v, (int, float)) or not isfinite(v):
            raise ValueError(f"bougie {bar.index}: {name} doit être fini")
    if (bar.high < max(bar.open, bar.close) or bar.low > min(bar.open, bar.close)
            or bar.high < bar.low or bar.volume < 0):
        raise ValueError(f"bougie {bar.index} incohérente")
    if bar.t_open.utcoffset() is None or bar.t_close.utcoffset() is None:
        raise ValueError("les horodatages doivent porter un fuseau")
    if bar.t_close.astimezone(timezone.utc) <= bar.t_open.astimezone(timezone.utc):
        raise ValueError("t_close doit être strictement après t_open")


class Context:
    def __init__(self, atr_len: int) -> None:
        if type(atr_len) is not int or atr_len < 1:
            raise ValueError("atr_len doit être un entier >= 1")
        self.atr_len = atr_len
        self.bars: list[Bar] = []
        self.tr: list[float] = []
        self.atr: list[float] = []

    @property
    def last(self) -> int:
        return len(self.bars) - 1

    def append(self, bar: Bar) -> None:
        validate_bar(bar)
        if bar.index != len(self.bars):
            raise ValueError(f"index attendu {len(self.bars)}, reçu {bar.index}")
        if self.bars and bar.t_open.astimezone(timezone.utc) < self.bars[-1].t_close.astimezone(timezone.utc):
            raise ValueError(f"bougie {bar.index} dupliquée ou chevauchant la précédente")
        self.bars.append(bar)
        if len(self.bars) == 1:
            tr = bar.high - bar.low
        else:
            pc = self.bars[-2].close
            tr = max(bar.high - bar.low, abs(bar.high - pc), abs(bar.low - pc))
        self.tr.append(tr)
        n = len(self.tr)
        if n <= self.atr_len:
            # Phase de chauffe : moyenne simple des TR disponibles (PROPOSITION).
            self.atr.append(sum(self.tr) / n)
        else:
            prev = self.atr[-1]
            self.atr.append((prev * (self.atr_len - 1) + tr) / self.atr_len)

    def highest(self, a: int, b: int) -> tuple[float, int]:
        """Plus haut sur [a, b] inclus ; à égalité, la première occurrence."""
        a = max(a, 0)
        b = min(b, self.last)
        best_p, best_i = self.bars[a].high, a
        for i in range(a + 1, b + 1):
            if self.bars[i].high > best_p:
                best_p, best_i = self.bars[i].high, i
        return best_p, best_i

    def lowest(self, a: int, b: int) -> tuple[float, int]:
        """Plus bas sur [a, b] inclus ; à égalité, la première occurrence."""
        a = max(a, 0)
        b = min(b, self.last)
        best_p, best_i = self.bars[a].low, a
        for i in range(a + 1, b + 1):
            if self.bars[i].low < best_p:
                best_p, best_i = self.bars[i].low, i
        return best_p, best_i
