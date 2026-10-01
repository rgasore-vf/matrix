"""R-OD-01 à R-OD-05 : zones d'offre/demande, mitigation, order flow, breaker.

Zone de demande (direction BULL) :
- distal   = plus bas de la BQA (extrême du swing d'origine) ;
- proximal = haut du corps de la BM (zone_proximal="body") ou plus haut de la BM ("wick") ;
             sans BM, plus haut de la BQA (zone = bougie OB entière).
Zone d'offre (BEAR) : symétrique.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .candles import is_doji, is_manipulative
from .config import Config
from .context import Context
from .pivots import Pivot
from .types import BEAR, BULL, Event, Kind

ACTIVE = "ACTIVE"
BROKEN = "BROKEN"


@dataclass
class Zone:
    zid: str
    direction: int
    proximal: float
    distal: float
    bqa_index: int
    bm_index: int | None
    confirm_index: int
    source: str            # "BOS_CHANGE", "BOS_CONTINUATION", "PIVOT", "BREAKER"
    decisional: bool
    doji_signature: bool
    validated: bool
    status: str = ACTIVE
    touches: int = 0
    broken_index: int | None = None
    odf_len: int = 1
    reacted: bool = False
    inside: bool = False
    meta: dict = field(default_factory=dict)

    @property
    def top(self) -> float:
        return max(self.proximal, self.distal)

    @property
    def bottom(self) -> float:
        return min(self.proximal, self.distal)


class ZoneBook:
    def __init__(self, cfg: Config, ctx: Context) -> None:
        self.cfg = cfg
        self.ctx = ctx
        self.zones: list[Zone] = []
        self._active: list[Zone] = []

    # -- construction -----------------------------------------------------------
    def build(self, direction: int, bqa: int, i: int, source: str, decisional: bool,
              validated: bool) -> Zone | None:
        bars = self.ctx.bars
        bm = None
        for b in range(bqa, bqa - self.cfg.bm_search_back - 1, -1):
            if b < 0:
                break
            atr_prev = self.ctx.atr[b - 1] if b >= 1 else None
            if is_manipulative(bars[b], direction, self.cfg, atr_prev):
                bm = b
                break
        q = bars[bqa]
        if direction == BULL:
            distal = q.low
            if bm is None:
                proximal = q.high
            elif self.cfg.zone_proximal == "body":
                proximal = max(bars[bm].open, bars[bm].close)
            else:
                proximal = bars[bm].high
        else:
            distal = q.high
            if bm is None:
                proximal = q.low
            elif self.cfg.zone_proximal == "body":
                proximal = min(bars[bm].open, bars[bm].close)
            else:
                proximal = bars[bm].low
        if (direction == BULL and proximal <= distal) or (direction == BEAR and proximal >= distal):
            proximal = q.high if direction == BULL else q.low
            bm = None
            if proximal == distal:
                return None
        doji_sig = is_doji(q, self.cfg) or any(
            is_doji(bars[k], self.cfg) for k in range(max(0, i - self.cfg.doji_window), i)
        )
        return Zone(
            zid=f"Z{'D' if direction == BULL else 'S'}:{bqa}:{i}",
            direction=direction, proximal=proximal, distal=distal,
            bqa_index=bqa, bm_index=bm, confirm_index=i, source=source,
            decisional=decisional, doji_signature=doji_sig, validated=validated,
        )

    def _zone_event(self, z: Zone) -> Event:
        anchor = z.bm_index if z.bm_index is not None and z.bm_index < z.bqa_index else z.bqa_index
        return Event(
            Kind.ZONE if z.source != "BREAKER" else Kind.BREAKER,
            z.confirm_index, anchor, z.direction, z.proximal, z.zid,
            {"proximal": z.proximal, "distal": z.distal, "bqa_index": z.bqa_index,
             "bm_index": z.bm_index, "source": z.source, "decisional": z.decisional,
             "doji_signature": z.doji_signature, "validated": z.validated},
        )

    def _link_odf(self, z: Zone) -> list[Event]:
        """R-OD-04 : la BQA de la nouvelle zone a « récupéré » la zone précédente de même sens."""
        bars = self.ctx.bars
        q = bars[z.bqa_index]
        for prev in reversed(self.zones):
            if prev is z or prev.direction != z.direction or prev.source == "BREAKER":
                continue
            if prev.bqa_index >= z.bqa_index or prev.confirm_index > z.bqa_index:
                continue
            if prev.broken_index is not None and prev.broken_index <= z.bqa_index:
                continue
            if z.direction == BULL:
                linked = q.low <= prev.proximal and q.close >= prev.distal
            else:
                linked = q.high >= prev.proximal and q.close <= prev.distal
            if linked:
                z.odf_len = prev.odf_len + 1
                return [Event(
                    Kind.ODF_LINK, z.confirm_index, z.bqa_index, z.direction, z.proximal,
                    f"ODF:{prev.zid}>{z.zid}",
                    {"from": prev.zid, "to": z.zid, "chain_len": z.odf_len,
                     "is_odf": z.odf_len >= self.cfg.odf_min_len},
                )]
            return []  # seule la zone précédente active de même sens est considérée
        return []

    def _add(self, z: Zone) -> list[Event]:
        self.zones.append(z)
        self._active.append(z)
        out = [self._zone_event(z)]
        if z.source != "BREAKER":
            out += self._link_odf(z)
        return out

    def on_structure(self, i: int, events: list[Event]) -> list[Event]:
        out: list[Event] = []
        for ev in events:
            if ev.kind not in (Kind.BOS_CHANGE, Kind.BOS_CONTINUATION):
                continue
            origin = ev.data["origin_index"]
            z = self.build(ev.direction, origin, i, ev.kind,
                           decisional=ev.kind == Kind.BOS_CHANGE, validated=True)
            if z is not None:
                out += self._add(z)
        return out

    def on_pivots(self, i: int, pivots: list[Pivot]) -> list[Event]:
        if self.cfg.zones_on != "all_pivots":
            return []
        out: list[Event] = []
        for pv in pivots:
            d = BULL if pv.side == "L" else BEAR
            z = self.build(d, pv.index, i, "PIVOT", decisional=False, validated=False)
            if z is not None:
                out += self._add(z)
        return out

    # -- cycle de vie -------------------------------------------------------------
    def update(self, i: int) -> list[Event]:
        bar = self.ctx.bars[i]
        out: list[Event] = []
        new_breakers: list[Zone] = []
        for z in self._active:
            if z.confirm_index >= i:
                continue
            if z.direction == BULL:
                broken = bar.close < z.distal
                touched = bar.low <= z.proximal
                reaction = touched and bar.close > z.proximal
            else:
                broken = bar.close > z.distal
                touched = bar.high >= z.proximal
                reaction = touched and bar.close < z.proximal
            if broken:
                z.status = BROKEN
                z.broken_index = i
                out.append(Event(Kind.ZONE_BROKEN, i, z.bqa_index, z.direction, z.distal,
                                 f"ZB:{z.zid}", {"zone": z.zid, "source": z.source}))
                if z.source != "BREAKER":
                    br = Zone(
                        zid=f"BRK:{z.zid}", direction=-z.direction,
                        proximal=z.distal, distal=z.proximal,
                        bqa_index=z.bqa_index, bm_index=z.bm_index, confirm_index=i,
                        source="BREAKER", decisional=False, doji_signature=z.doji_signature,
                        validated=False, meta={"from": z.zid},
                    )
                    new_breakers.append(br)
            elif touched and not z.inside:
                # R-OD-03 : une touche = début d'un épisode de contact (le prix revient dans la zone).
                z.inside = True
                z.touches += 1
                out.append(Event(Kind.ZONE_TOUCH, i, z.bqa_index, z.direction, z.proximal,
                                 f"ZT:{z.zid}:{z.touches}",
                                 {"zone": z.zid, "touch": z.touches, "source": z.source}))
            elif not touched:
                z.inside = False
            # R-OD-05 : réaction = contact puis clôture du bon côté du bord proximal.
            if not broken and z.source == "BREAKER" and reaction and not z.reacted:
                z.reacted = True
                z.validated = True
                out.append(Event(Kind.BREAKER_REACTION, i, z.bqa_index, z.direction,
                                 z.proximal, f"BR:{z.zid}", {"zone": z.zid}))
        if any(z.status != ACTIVE for z in self._active):
            self._active = [z for z in self._active if z.status == ACTIVE]
        for br in new_breakers:
            out += self._add(br)
        return out
