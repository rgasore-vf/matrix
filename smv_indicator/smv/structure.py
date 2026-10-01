"""R-ST-04 à R-ST-07 et R-LQ-05 : automate de structure majeure.

Vocabulaire (tendance haussière, d = BULL ; la baisse est symétrique) :
- prot     : niveau protégé (HL majeur). Une clôture au-delà = BOS de changement de tendance.
- ref      : HH « fixé » (pivot confirmé égal à l'extrême de la jambe). Une clôture
             au-delà = BOS de continuation. Sans retracement (pas de pivot), pas de ref.
- leg_ext  : extrême courant de la jambe (mèches comprises).
- origin   : extrême du retracement d'où part l'impulsion cassante ; ancre des zones.

Ordre de traitement d'une bougie i (déterministe) :
1. tests de cassure avec l'état connu à la fin de i-1 ;
2. mise à jour de l'extrême de jambe avec la bougie i ;
3. intégration des pivots confirmés à la clôture de i.
"""
from __future__ import annotations

from .config import Config
from .context import Context
from .pivots import Pivot, PivotDetector
from .types import BEAR, BULL, NONE, Event, Kind


class StructureTracker:
    def __init__(self, cfg: Config, ctx: Context, pivots: PivotDetector) -> None:
        self.cfg = cfg
        self.ctx = ctx
        self.pivots = pivots
        self.trend = NONE
        self.prot: tuple[float, int] | None = None
        self.ref: tuple[float, int] | None = None
        self.leg_ext: tuple[float, int] | None = None
        self.leg_start = 0
        self.fail_done = False
        self.prot_swept_at: int | None = None
        self.last_ph: Pivot | None = None
        self.last_pl: Pivot | None = None
        self._last_leg_pivot: Pivot | None = None

    # -- outils directionnels -------------------------------------------------
    def _ext(self, d: int, a: int, b: int) -> tuple[float, int]:
        return self.ctx.highest(a, b) if d == BULL else self.ctx.lowest(a, b)

    def _beyond(self, price: float, level: float, d: int) -> bool:
        eps = self.cfg.bos_eps
        return price > level + eps if d == BULL else price < level - eps

    # -- mise à jour ----------------------------------------------------------
    def update(self, i: int, new_pivots: list[Pivot]) -> list[Event]:
        bar = self.ctx.bars[i]
        events: list[Event] = []

        if self.trend == NONE:
            events += self._try_init(i, bar.close)
        else:
            events += self._check_breaks(i)

        # 2. extrême de jambe
        if self.trend == BULL and self.leg_ext is not None and bar.high > self.leg_ext[0]:
            self.leg_ext = (bar.high, i)
        elif self.trend == BEAR and self.leg_ext is not None and bar.low < self.leg_ext[0]:
            self.leg_ext = (bar.low, i)

        # 3. pivots confirmés à la clôture de i
        for pv in new_pivots:
            if pv.side == "H":
                self.last_ph = pv
            else:
                self.last_pl = pv
            if self.trend != NONE:
                events += self._integrate_pivot(i, pv)
        return events

    def _try_init(self, i: int, close: float) -> list[Event]:
        for d, pv in ((BULL, self.last_ph), (BEAR, self.last_pl)):
            if pv is not None and self._beyond(close, pv.price, d):
                origin = self._ext(-d, pv.index, i)
                self._start_leg(d, prot=origin, start=origin[1], i=i)
                return [Event(
                    Kind.TREND_INIT, i, pv.index, d, pv.price, f"INIT:{i}",
                    {"origin_index": origin[1], "origin_price": origin[0]},
                )]
        return []

    def _start_leg(self, d: int, prot: tuple[float, int], start: int, i: int) -> None:
        self.trend = d
        self.prot = prot
        self.ref = None
        self.leg_start = start
        self.leg_ext = self._ext(d, start, i)
        self.fail_done = False
        self.prot_swept_at = None
        self._last_leg_pivot = None

    def _check_breaks(self, i: int) -> list[Event]:
        d = self.trend
        bar = self.ctx.bars[i]
        assert self.prot is not None
        # BOS de changement de tendance : clôture au-delà du niveau protégé.
        if self._beyond(bar.close, self.prot[0], -d):
            broken = self.prot
            new_prot = self._ext(d, broken[1], i)  # extrême de l'ancienne tendance = origine
            ev = Event(
                Kind.BOS_CHANGE, i, broken[1], -d, broken[0], f"BOSC:{i}",
                {"origin_index": new_prot[1], "origin_price": new_prot[0],
                 "major_mode": self.cfg.major_mode},
            )
            self._start_leg(-d, prot=new_prot, start=new_prot[1], i=i)
            return [ev]
        # The old protected wick and a continuation break are independent facts.
        events: list[Event] = []
        wick = bar.low if d == BULL else bar.high
        crossed = wick < self.prot[0] if d == BULL else wick > self.prot[0]
        if crossed and self.prot_swept_at is None:
            self.prot_swept_at = i
            events.append(Event(Kind.PROTECTED_SWEEP, i, self.prot[1], -d, self.prot[0],
                                f"PSW:{i}", {"trend": d}))
        # BOS de continuation : clôture au-delà du dernier extrême fixé.
        if self.ref is not None and self._beyond(bar.close, self.ref[0], d):
            ref = self.ref
            origin = self._ext(-d, ref[1], i)
            events.append(Event(
                Kind.BOS_CONTINUATION, i, ref[1], d, ref[0], f"BOS:{i}",
                {"origin_index": origin[1], "origin_price": origin[0],
                 "major_mode": self.cfg.major_mode},
            ))
            # R-LQ-05 : pivots du retracement qui n'ont pas donné le BOS.
            side = "L" if d == BULL else "H"
            plist = self.pivots.lows if side == "L" else self.pivots.highs
            # Pivots are ordered by anchor: stop once the retracement is left.
            in_retr = []
            for p in reversed(plist):
                if p.index <= ref[1]:
                    break
                if p.index <= i and p.confirm_index <= i:
                    in_retr.append(p)
            in_retr.reverse()
            if self.cfg.major_mode == "A":
                idm = [p for p in in_retr if p.index != origin[1]]
                new_prot = origin
            else:
                idm = in_retr
                new_prot = self.prot
            for p in idm:
                events.append(Event(
                    Kind.INDUCEMENT, i, p.index, NONE, p.price, f"IDM:{p.ref}",
                    {"level_ref": p.ref, "side": side, "trend": d},
                ))
            self.prot = new_prot
            self.ref = None
            self.leg_start = origin[1]
            self.leg_ext = self._ext(d, origin[1], i)
            self.fail_done = False
            self.prot_swept_at = None
            self._last_leg_pivot = None
            return events
        return events

    def _integrate_pivot(self, i: int, pv: Pivot) -> list[Event]:
        d = self.trend
        events: list[Event] = []
        trend_side = "H" if d == BULL else "L"
        if pv.side != trend_side or pv.index < self.leg_start:
            return events
        assert self.leg_ext is not None
        is_extreme = pv.price >= self.leg_ext[0] if d == BULL else pv.price <= self.leg_ext[0]
        if is_extreme:
            self.ref = (pv.price, pv.index)
        # R-ST-07 : premier sommet plus bas (resp. creux plus haut) de la jambe.
        if not self.fail_done:
            failed = pv.label == ("LH" if d == BULL else "HL")
            if failed:
                self.fail_done = True
                climax = self._ext(d, self.leg_start, pv.index)        # BC (hausse) / SC (baisse)
                ar = self._ext(-d, climax[1], pv.index)                 # AR
                events.append(Event(
                    Kind.FAIL, i, pv.index, -d, pv.price, f"FAIL:{pv.ref}",
                    {"prior_trend": d, "climax_index": climax[1], "climax_price": climax[0],
                     "ar_index": ar[1], "ar_price": ar[0], "st_ref": pv.ref},
                ))
        self._last_leg_pivot = pv
        return events

    def snapshot(self) -> dict:
        return {
            "trend": self.trend,
            "prot": self.prot,
            "ref": self.ref,
            "leg_ext": self.leg_ext,
            "leg_start": self.leg_start,
        }
