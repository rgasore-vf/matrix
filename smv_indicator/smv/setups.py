"""R-SE-01 à R-SE-03, R-GS-03, §9 : setups « golden entry » et « concept entry ».

AVERTISSEMENT (CALIBRATION §4) : sur EURUSD et XAUUSD 2015-2021, ces setups n'ont pas
d'espérance positive mesurée après coûts. Ce sont des repères de lecture, pas des signaux.

Un setup naît à la clôture du BOS qui crée sa zone. Il est suivi bougie par bougie :
SETUP -> SETUP_TRIGGERED (le prix touche l'entrée) -> SETUP_CLOSED (stop ou cible),
ou SETUP_EXPIRED (pas de déclenchement dans le délai, ou retournement de tendance).

GOLDEN (Modules 7-8) : une consolidation est ouverte ; au moins une prise de liquidité a eu lieu
sur la borne opposée au sens du trade (borne basse pour un achat : STB/spring ; borne haute pour
une vente : UT/UTAD) ; un BOS dans le sens du trade (« intention ») survient ensuite et crée une
zone ; l'entrée est le TEST de cette zone dans les `test_max_bars` bougies (PROPOSITION ;
délai non chiffré dans les sources Wyckoff, CALIBRATION Q-11).

CONCEPT (Module 9) : tendance d ; un inducement révélé dans cette tendance a été pris ; le BOS
suivant dans le sens d crée une zone ; l'entrée est le retour sur cette zone dans
`setup_expiry_bars` bougies.

Entrée : bord proximal de la zone (ordre limite). Stop : bord distal (mèche de la BQA).
Cibles : niveaux de liquidité intacts au-delà de l'entrée au moment du setup, du plus proche au
plus lointain (R-LQ-02). Politique de sortie mesurée : tout sur T1 (le dépôt laisse la gestion des
partiels à chacun). Ordre intra-bougie inconnu, deux règles prudentes : si une bougie touche le stop
et la cible, le stop est retenu ; sur la bougie de déclenchement, seul le stop est évalué (sans
cette règle, le backtest gagnait aussi sur des séries mélangées : biais d'ordre intra-bougie).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .config import Config
from .context import Context
from .liquidity import LiquidityBook
from .ranges import RangeTracker
from .structure import StructureTracker
from .types import BULL, Event, Kind

SETUP = Kind.SETUP
SETUP_TRIGGERED = Kind.SETUP_TRIGGERED
SETUP_CLOSED = Kind.SETUP_CLOSED
SETUP_EXPIRED = Kind.SETUP_EXPIRED


@dataclass
class Setup:
    sid: str
    kind: str              # "GOLDEN" ou "CONCEPT"
    direction: int
    entry: float
    stop: float
    targets: list
    created: int
    deadline: int
    zone: str
    label: str
    triggered: int | None = None
    closed: bool = False
    mfe_r: float = 0.0
    meta: dict = field(default_factory=dict)

    @property
    def risk(self) -> float:
        return abs(self.entry - self.stop)


class SetupTracker:
    def __init__(self, cfg: Config, ctx: Context, structure: StructureTracker,
                 liquidity: LiquidityBook, ranges: RangeTracker) -> None:
        self.cfg = cfg
        self.ctx = ctx
        self.structure = structure
        self.liquidity = liquidity
        self.ranges = ranges
        self.active: list[Setup] = []
        self.idm_levels: dict[str, int] = {}     # niveau -> sens de la tendance qui l'a révélé
        self.idm_taken_dir = 0                   # sens dont un inducement a été pris (0 = aucun)
        self.range_sweep_at: dict[tuple[str, str], int] = {}  # (range, côté) -> dernière prise

    # -- suivi des setups existants (bougie i, setups créés avant i) -----------------
    def update(self, i: int) -> list[Event]:
        bar = self.ctx.bars[i]
        out: list[Event] = []
        keep: list[Setup] = []
        for s in self.active:
            if s.created >= i:
                keep.append(s)
                continue
            d = s.direction
            if s.triggered is None:
                touched = bar.low <= s.entry if d == BULL else bar.high >= s.entry
                if not touched:
                    if i >= s.deadline:
                        out.append(self._ev(SETUP_EXPIRED, i, s, {"reason": "not_triggered"}))
                        continue
                    keep.append(s)
                    continue
                s.triggered = i
                out.append(self._ev(SETUP_TRIGGERED, i, s, {}))
            # déclenché (éventuellement sur cette bougie) : stop puis cible
            stop_hit = bar.low <= s.stop if d == BULL else bar.high >= s.stop
            if stop_hit:
                out.append(self._close(i, s, -1.0, "stop"))
                continue
            if s.triggered == i:
                # Bougie de déclenchement : l'ordre intra-bougie est inconnu ; le plus haut
                # (achat) a pu être atteint AVANT le retour sur l'entrée. Seul le stop est
                # évalué ; la cible ne compte qu'à partir de la bougie suivante (prudent).
                keep.append(s)
                continue
            fav = (bar.high - s.entry) if d == BULL else (s.entry - bar.low)
            s.mfe_r = max(s.mfe_r, fav / s.risk)
            t1 = s.targets[0][0]
            if (d == BULL and bar.high >= t1) or (d != BULL and bar.low <= t1):
                out.append(self._close(i, s, abs(t1 - s.entry) / s.risk, "target1"))
                continue
            keep.append(s)
        self.active = keep
        return out

    def _close(self, i: int, s: Setup, r: float, reason: str) -> Event:
        s.closed = True
        return self._ev(SETUP_CLOSED, i, s, {"reason": reason, "r": round(r, 4),
                                             "bars_in_trade": i - (s.triggered or i),
                                             "mfe_r": round(s.mfe_r, 4)})

    def _ev(self, kind: str, i: int, s: Setup, extra: dict) -> Event:
        return Event(kind, i, s.created, s.direction, s.entry, f"{kind}:{s.sid}",
                     {"setup": s.sid, "type": s.kind, **extra})

    # -- création (événements de la bougie i) -------------------------------------
    def on_events(self, i: int, events: list[Event]) -> list[Event]:
        out: list[Event] = []
        for ev in events:
            if ev.kind == Kind.RANGE_SWEEP:
                self.range_sweep_at[(ev.data["range"], ev.data["side"])] = i
            elif ev.kind == Kind.INDUCEMENT:
                self.idm_levels[ev.data["level_ref"]] = ev.data["trend"]
            elif ev.kind in (Kind.LIQ_CLEAN, Kind.LIQ_BOS):
                d = self.idm_levels.pop(ev.data["level"], 0)
                if d != 0 and d == self.structure.trend:
                    self.idm_taken_dir = d
            elif ev.kind in (Kind.BOS_CHANGE, Kind.TREND_INIT):
                self.idm_taken_dir = 0
                # retournement : les setups non déclenchés dans l'autre sens expirent
                for s in list(self.active):
                    if s.triggered is None and s.direction != ev.direction:
                        self.active.remove(s)
                        out.append(self._ev(SETUP_EXPIRED, i, s, {"reason": "trend_change"}))
        for ev in events:
            if ev.kind != Kind.ZONE or ev.data["source"] not in (Kind.BOS_CHANGE, Kind.BOS_CONTINUATION):
                continue
            d = ev.direction
            kind, label, deadline = self._qualify(i, d, ev)
            if kind is None:
                continue
            entry, stop = ev.data["proximal"], ev.data["distal"]
            risk = abs(entry - stop)
            atr = self.ctx.atr[i]
            targets = [(lv.price, lv.lid) for lv in self.liquidity.intact_targets(entry, d)]
            reject = None
            if risk <= 0:
                reject = "zero_risk"
            elif risk > self.cfg.sl_max_atr * atr:
                reject = "sl_too_wide"
            elif not targets:
                reject = "no_target"
            sid = f"{kind[0]}{i}:{ev.ref}"
            data = {"setup": sid, "type": kind, "label": label, "zone": ev.ref, "stop": stop,
                    "risk": risk, "risk_atr": round(risk / atr, 3) if atr > 0 else None,
                    "targets": [t[0] for t in targets[:3]],
                    "rr": [round(abs(t[0] - entry) / risk, 2) for t in targets[:3]] if risk > 0 else [],
                    "rejected": reject, "deadline": deadline}
            out.append(Event(SETUP, i, ev.anchor_index, d, entry, sid, data))
            if reject is None:
                self.active.append(Setup(sid, kind, d, entry, stop, targets, i, deadline, ev.ref, label))
                if kind == "CONCEPT":
                    self.idm_taken_dir = 0
        return out

    def _qualify(self, i: int, d: int, zone_ev: Event):
        r = self.ranges.current
        side = "L" if d == BULL else "H"
        if r is not None and r.open_index < i:
            swept = self.range_sweep_at.get((r.rid, side))
            open_or_just_closed = (not r.closed) or r.exit_index == i
            if swept is not None and swept <= i and open_or_just_closed:
                n = r.sweeps[side]
                return "GOLDEN", self.ranges.label(r, side, n), i + self.cfg.test_max_bars
        if self.idm_taken_dir == d and zone_ev.data["source"] == Kind.BOS_CONTINUATION:
            return "CONCEPT", "IDM", i + self.cfg.setup_expiry_bars
        return None, None, None
