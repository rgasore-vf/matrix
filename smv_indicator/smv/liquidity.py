"""R-LQ-01 à R-LQ-03 : niveaux de liquidité (intact, clean, BOS) et EQH/EQL.

Un niveau haut L est INTACT tant qu'aucune bougie ultérieure n'a dépassé L.
À la première bougie i qui le dépasse :
- close[i] > L  -> LIQ_BOS   (statut final)
- sinon         -> LIQ_CLEAN (prise de liquidité en mèche, statut final)
Les niveaux bas sont symétriques.
"""
from __future__ import annotations

import heapq
from dataclasses import dataclass

from .config import Config
from .context import Context
from .pivots import Pivot
from .types import BEAR, BULL, NONE, Event, Kind

INTACT = "INTACT"
CLEAN = "CLEAN"
BOS = "BOS"


@dataclass
class Level:
    lid: str
    side: str            # "H" ou "L"
    price: float
    anchor_index: int
    confirm_index: int
    source: str          # "PIVOT" ou "SIGNATURE"
    status: str = INTACT
    taken_index: int | None = None


class LiquidityBook:
    def __init__(self, cfg: Config, ctx: Context) -> None:
        self.cfg = cfg
        self.ctx = ctx
        self.levels: dict[str, Level] = {}
        self._intact: list[Level] = []        # ordre de création (pour EQ et cibles)
        self._seq = 0
        self._heap_h: list[tuple[float, int, Level]] = []   # hauts intacts, du plus bas au plus haut
        self._heap_l: list[tuple[float, int, Level]] = []   # bas intacts, du plus haut au plus bas (prix négatif)

    def update(self, i: int) -> list[Event]:
        """Statuts des niveaux existants, avec la bougie i (tous créés avant i).

        Les niveaux sont rangés dans deux tas par prix : seuls ceux que la bougie atteint
        sont examinés. Les événements sont émis dans l'ordre de création des niveaux."""
        bar = self.ctx.bars[i]
        hit: list[tuple[int, Level]] = []
        while self._heap_h and self._heap_h[0][0] < bar.high:
            _, seq, lv = heapq.heappop(self._heap_h)
            hit.append((seq, lv))
        while self._heap_l and -self._heap_l[0][0] > bar.low:
            _, seq, lv = heapq.heappop(self._heap_l)
            hit.append((seq, lv))
        out: list[Event] = []
        for _, lv in sorted(hit, key=lambda x: x[0]):
            if lv.side == "H":
                closed, d = bar.close > lv.price, BULL
            else:
                closed, d = bar.close < lv.price, BEAR
            lv.status = BOS if closed else CLEAN
            lv.taken_index = i
            out.append(Event(
                Kind.LIQ_BOS if closed else Kind.LIQ_CLEAN, i, lv.anchor_index, d, lv.price,
                f"{'LB' if closed else 'LC'}:{lv.lid}", {"level": lv.lid, "source": lv.source},
            ))
        if hit:
            self._intact = [x for x in self._intact if x.status == INTACT]
        return out

    def _add(self, lv: Level) -> Event:
        self.levels[lv.lid] = lv
        self._intact.append(lv)
        self._seq += 1
        if lv.side == "H":
            heapq.heappush(self._heap_h, (lv.price, self._seq, lv))
        else:
            heapq.heappush(self._heap_l, (-lv.price, self._seq, lv))
        return Event(Kind.LIQ_LEVEL, lv.confirm_index, lv.anchor_index, NONE, lv.price,
                     lv.lid, {"side": lv.side, "source": lv.source})

    def on_pivots(self, i: int, pivots: list[Pivot]) -> list[Event]:
        out: list[Event] = []
        for pv in pivots:
            # R-LQ-03 : comparaison avec le niveau intact de même côté le plus récent
            # dont l'écart est sous la tolérance.
            tol = self.cfg.eq_tol_atr * self.ctx.atr[pv.index]
            match = None
            for lv in reversed(self._intact):
                if lv.side == pv.side and lv.source == "PIVOT" and lv.anchor_index < pv.index:
                    if abs(lv.price - pv.price) <= tol:
                        match = lv
                        break
                if pv.index - lv.anchor_index > self.cfg.eq_max_gap:
                    break
            out.append(self._add(Level(pv.ref, pv.side, pv.price, pv.index, i, "PIVOT")))
            if match is not None:
                ext = max(match.price, pv.price) if pv.side == "H" else min(match.price, pv.price)
                out.append(Event(
                    Kind.EQUAL_LEVELS, i, match.anchor_index, NONE, ext,
                    f"EQ{pv.side}:{match.anchor_index}:{pv.index}",
                    {"side": pv.side, "first": match.lid, "second": pv.ref, "tolerance": tol},
                ))
        return out

    def on_signatures(self, i: int, events: list[Event]) -> list[Event]:
        out: list[Event] = []
        for ev in events:
            if ev.kind != Kind.LIQ_SIGNATURE:
                continue
            side = ev.data["side"]
            out.append(self._add(Level(ev.ref, side, ev.price, ev.anchor_index, i, "SIGNATURE")))
        return out

    def intact_targets(self, entry: float, direction: int) -> list[Level]:
        """R-LQ-02 : niveaux intacts au-delà de l'entrée, du plus proche au plus lointain."""
        if direction == BULL:
            lv = [x for x in self._intact if x.side == "H" and x.price > entry]
            return sorted(lv, key=lambda x: x.price)
        lv = [x for x in self._intact if x.side == "L" and x.price < entry]
        return sorted(lv, key=lambda x: -x.price)
