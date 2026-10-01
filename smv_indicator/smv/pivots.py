"""R-ST-02 / R-ST-03 : pivots fractals et étiquetage HH/HL/LH/LL.

Un pivot en p n'est connu qu'à la clôture de p + pivot_right.
"""
from __future__ import annotations

from dataclasses import dataclass

from .config import Config
from .context import Context
from .types import NONE, Event, Kind


@dataclass(frozen=True)
class Pivot:
    side: str          # "H" ou "L"
    index: int         # ancrage (bougie de l'extrême)
    price: float
    confirm_index: int
    label: str         # HH, LH, EH, HL, LL, EL, ou "" pour le premier

    @property
    def ref(self) -> str:
        return f"P{self.side}:{self.index}"


class PivotDetector:
    def __init__(self, cfg: Config, ctx: Context) -> None:
        self.cfg = cfg
        self.ctx = ctx
        self.highs: list[Pivot] = []
        self.lows: list[Pivot] = []

    def update(self, i: int) -> tuple[list[Pivot], list[Event]]:
        nl, nr = self.cfg.pivot_left, self.cfg.pivot_right
        p = i - nr
        if p - nl < 0:
            return [], []
        bars = self.ctx.bars
        new: list[Pivot] = []
        h = bars[p].high
        if all(h > bars[p - j].high for j in range(1, nl + 1)) and all(
            h >= bars[p + j].high for j in range(1, nr + 1)
        ):
            prev = self.highs[-1] if self.highs else None
            label = "" if prev is None else ("HH" if h > prev.price else "LH" if h < prev.price else "EH")
            pv = Pivot("H", p, h, i, label)
            self.highs.append(pv)
            new.append(pv)
        lo = bars[p].low
        if all(lo < bars[p - j].low for j in range(1, nl + 1)) and all(
            lo <= bars[p + j].low for j in range(1, nr + 1)
        ):
            prev = self.lows[-1] if self.lows else None
            label = "" if prev is None else ("HL" if lo > prev.price else "LL" if lo < prev.price else "EL")
            pv = Pivot("L", p, lo, i, label)
            self.lows.append(pv)
            new.append(pv)
        events = [
            Event(
                Kind.PIVOT_HIGH if pv.side == "H" else Kind.PIVOT_LOW,
                confirm_index=i,
                anchor_index=pv.index,
                direction=NONE,
                price=pv.price,
                ref=pv.ref,
                data={"label": pv.label},
            )
            for pv in new
        ]
        return new, events
