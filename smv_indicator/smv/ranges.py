"""R-CE-01, R-CE-02, R-GS-02 : consolidation (cause) et décompte de liquidité externe.

EXPÉRIMENTAL. Les libellés Wyckoff (STB, SPRING, UA, UT, UTAD, MSO) sont des
CANDIDATS : ils ne sont confirmés ou infirmés qu'à la sortie de la consolidation
(événement RANGE_EXIT, champ « outcome »). Rien n'est réécrit dans le passé.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .config import Config
from .context import Context
from .types import BEAR, BULL, NONE, Event, Kind

# Libellés par contexte et par côté, dans l'ordre des prises successives.
LABELS = {
    # tendance précédente baissière -> accumulation attendue
    BEAR: {"L": ("STB", "SPRING"), "H": ("UA",)},
    # tendance précédente haussière -> distribution attendue
    BULL: {"H": ("UT", "UTAD"), "L": ("MSO",)},
}


@dataclass
class Range:
    rid: str
    prior_trend: int
    low: float
    high: float
    open_index: int
    st_ref: str
    sweeps: dict = field(default_factory=lambda: {"H": 0, "L": 0})
    intention: int = NONE
    fail_taken: bool = False
    complete: bool = False
    closed: bool = False
    exit_index: int | None = None  # bougie de clôture validée (RANGE_EXIT) ; None si remplacée par un FAIL
    pending: tuple | None = None   # (direction, index de début, extrême) d'une sortie non validée
    outside: dict = field(default_factory=lambda: {"H": False, "L": False})  # épisode de prise en cours


class RangeTracker:
    def __init__(self, cfg: Config, ctx: Context) -> None:
        self.cfg = cfg
        self.ctx = ctx
        self.current: Range | None = None
        self.history: list[Range] = []

    def label(self, r: Range, side: str, n: int) -> str:
        seq = LABELS[r.prior_trend][side]
        return seq[min(n, len(seq)) - 1] if n <= len(seq) else f"{seq[-1]}+{n - len(seq)}"

    def update(self, i: int) -> list[Event]:
        """Sortie validée après `range_accept_bars` clôtures consécutives hors bornes
        (PROPOSITION) ; une excursion en clôture qui revient dans la fourchette avant
        validation est comptée comme une prise de liquidité (UT, spring... peuvent clôturer
        brièvement dehors, RESEARCH §3.1)."""
        r = self.current
        if r is None or r.closed or r.open_index >= i:
            return []
        bar = self.ctx.bars[i]
        out: list[Event] = []
        beyond = BULL if bar.close > r.high else BEAR if bar.close < r.low else NONE
        resolved_side = None
        if r.pending is not None:
            d, start, ext = r.pending
            if beyond == d:
                ext = max(ext, bar.high) if d == BULL else min(ext, bar.low)
                r.pending = (d, start, ext)
            else:
                # Recovered close excursion. Keep the wick episode status so
                # its same-side continuation is not counted a second time.
                r.pending = None
                resolved_side = "H" if d == BULL else "L"
                if not r.outside[resolved_side]:
                    out += self._sweep(r, i, resolved_side, start, ext)
                r.outside[resolved_side] = bar.high > r.high if d == BULL else bar.low < r.low
        if beyond != NONE and r.pending is None:
            r.pending = (beyond, i, bar.high if beyond == BULL else bar.low)
        # Une prise = un épisode : on compte la première bougie qui dépasse la borne en mèche ;
        # les bougies suivantes qui dépassent encore appartiennent au même épisode.
        for side, crossed in (("H", bar.high > r.high), ("L", bar.low < r.low)):
            if side == resolved_side or (r.pending is not None and side == ("H" if beyond == BULL else "L")):
                continue
            if crossed and not r.outside[side]:
                out += self._sweep(r, i, side, i, bar.high if side == "H" else bar.low)
            r.outside[side] = crossed
        if r.pending is not None:
            d, start, _ = r.pending
            if i - start + 1 >= self.cfg.range_accept_bars:
                return out + self._exit(r, i, d, start)
        out += self._check_complete(r, i)
        return out

    def _sweep(self, r: Range, i: int, side: str, anchor: int, price: float) -> list[Event]:
        r.sweeps[side] += 1
        n = r.sweeps[side]
        return [Event(
            Kind.RANGE_SWEEP, i, anchor, BULL if side == "H" else BEAR, price,
            f"RS:{r.rid}:{side}{n}",
            {"range": r.rid, "side": side, "count": n, "label_candidate": self.label(r, side, n)},
        )]

    def _exit(self, r: Range, i: int, d: int, start: int) -> list[Event]:
        expected = -r.prior_trend
        r.closed = True
        r.exit_index = i
        r.pending = None
        return [Event(
            Kind.RANGE_EXIT, i, start, d, self.ctx.bars[i].close, f"RX:{r.rid}",
            {"range": r.rid, "expected": expected,
             "outcome": "confirmed" if d == expected else "invalidated",
             "sweeps_high": r.sweeps["H"], "sweeps_low": r.sweeps["L"],
             "wyckoff_type": self._type(r, d), "duration": i - r.open_index},
        )]

    @staticmethod
    def _type(r: Range, exit_dir: int) -> str:
        """Type 1 (deux prises sur la borne opposée à la sortie) ou type 2 (une seule)."""
        side = "L" if exit_dir == BULL else "H"
        n = r.sweeps[side]
        return "type1" if n >= 2 else "type2" if n == 1 else "none"

    def _check_complete(self, r: Range, i: int) -> list[Event]:
        took = r.fail_taken or (r.sweeps["H"] + r.sweeps["L"]) > 0
        if not r.complete and took and r.intention != NONE:
            r.complete = True
            return [Event(Kind.CAUSE_COMPLETE, i, r.open_index, r.intention, 0.0,
                          f"CC:{r.rid}", {"range": r.rid})]
        return []

    def on_events(self, i: int, events: list[Event]) -> list[Event]:
        out: list[Event] = []
        r = self.current
        for ev in events:
            if ev.kind == Kind.FAIL:
                d = ev.data["prior_trend"]
                if d == BULL:
                    lo, hi = ev.data["ar_price"], ev.data["climax_price"]
                else:
                    lo, hi = ev.data["climax_price"], ev.data["ar_price"]
                if r is not None and not r.closed:
                    r.closed = True
                nr = Range(f"R:{i}", d, lo, hi, i, ev.data["st_ref"])
                self.current = nr
                self.history.append(nr)
                out.append(Event(
                    Kind.RANGE_OPEN, i, ev.data["climax_index"], -d, hi, nr.rid,
                    {"low": lo, "high": hi, "prior_trend": d,
                     "climax_index": ev.data["climax_index"], "ar_index": ev.data["ar_index"],
                     "st_ref": ev.data["st_ref"],
                     "context": "accumulation?" if d == BEAR else "distribution?"},
                ))
                r = nr
            elif r is not None and not r.closed and r.open_index < i:
                if ev.kind in (Kind.BOS_CHANGE, Kind.BOS_CONTINUATION) and r.intention == NONE:
                    r.intention = ev.direction
                    out.append(Event(Kind.RANGE_INTENTION, i, ev.anchor_index, ev.direction,
                                     ev.price, f"RI:{r.rid}", {"range": r.rid, "bos": ev.ref}))
                    out += self._check_complete(r, i)
                elif ev.kind in (Kind.LIQ_CLEAN, Kind.LIQ_BOS) and ev.data.get("level") == r.st_ref:
                    if not r.fail_taken:
                        r.fail_taken = True
                        out += self._check_complete(r, i)
        return out
