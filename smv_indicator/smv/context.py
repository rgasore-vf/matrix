"""Historique des bougies closes et indicateurs causaux (ATR de Wilder).

Le contexte ne contient que des bougies closes. Toute lecture se fait sur des
indices <= dernier indice ajouté ; aucune fonction ne lit au-delà.
"""
from __future__ import annotations

from .types import Bar


class Context:
    def __init__(self, atr_len: int) -> None:
        self.atr_len = atr_len
        self.bars: list[Bar] = []
        self.tr: list[float] = []
        self.atr: list[float] = []

    @property
    def last(self) -> int:
        return len(self.bars) - 1

    def append(self, bar: Bar) -> None:
        if bar.index != len(self.bars):
            raise ValueError(f"index attendu {len(self.bars)}, reçu {bar.index}")
        if bar.high < max(bar.open, bar.close) or bar.low > min(bar.open, bar.close):
            raise ValueError(f"bougie {bar.index} incohérente : {bar}")
        if self.bars and bar.t_open < self.bars[-1].t_open:
            raise ValueError(f"bougie {bar.index} non chronologique")
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
