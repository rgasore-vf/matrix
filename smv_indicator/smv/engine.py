"""Orchestrateur : consomme des bougies closes une par une et produit un journal
d'événements en ajout seul (STRATEGY_SPEC §0.5, ARCHITECTURE §3).

Ordre de traitement d'une bougie i :
 1. ajout au contexte (ATR) ;
 2. statuts des objets créés AVANT i : liquidités, zones, consolidation, setups ;
 3. détection de ce qui devient vrai à la clôture de i : pivots, structure,
    zones issues des BOS, niveaux de liquidité, signatures, consolidation, setups ;
 4. marqueurs optionnels (imbalance, sessions, fenêtre mensuelle).
Un objet créé à la clôture de i n'est mis à jour qu'à partir de i + 1.
"""
from __future__ import annotations

from typing import Iterable

from .candles import CandleScanner
from .config import Config
from .context import Context
from .liquidity import LiquidityBook
from .pivots import PivotDetector
from .ranges import RangeTracker
from .setups import SetupTracker
from .structure import StructureTracker
from .timing import ImbalanceScanner, MonthWindow, SessionMarker
from .types import Bar, Event
from .zones import ZoneBook


class Engine:
    def __init__(self, cfg: Config | None = None) -> None:
        self.cfg = cfg or Config()
        self.ctx = Context(self.cfg.atr_len)
        self.pivots = PivotDetector(self.cfg, self.ctx)
        self.structure = StructureTracker(self.cfg, self.ctx, self.pivots)
        self.zones = ZoneBook(self.cfg, self.ctx)
        self.liquidity = LiquidityBook(self.cfg, self.ctx)
        self.candles = CandleScanner(self.cfg, self.ctx)
        self.ranges = RangeTracker(self.cfg, self.ctx)
        self.setups = (SetupTracker(self.cfg, self.ctx, self.structure, self.liquidity, self.ranges)
                       if self.cfg.enable_setups else None)
        self.imbalance = ImbalanceScanner(self.cfg, self.ctx) if self.cfg.enable_imbalance else None
        self.sessions = SessionMarker(self.cfg, self.ctx) if self.cfg.enable_sessions else None
        self.month = MonthWindow(self.cfg, self.ctx) if self.cfg.enable_sessions else None
        self.log: list[Event] = []

    def on_bar(self, bar: Bar) -> list[Event]:
        """Traite une bougie CLOSE et retourne les événements devenus vrais à sa clôture."""
        self.ctx.append(bar)
        i = bar.index
        ev: list[Event] = []
        # 2. objets antérieurs
        ev += self.liquidity.update(i)
        ev += self.zones.update(i)
        ev += self.ranges.update(i)
        if self.setups is not None:
            ev += self.setups.update(i)
        # 3. nouveautés de la bougie i
        new_pivots, pev = self.pivots.update(i)
        ev += pev
        sev = self.structure.update(i, new_pivots)
        ev += sev
        ev += self.zones.on_structure(i, sev)
        ev += self.zones.on_pivots(i, new_pivots)
        ev += self.liquidity.on_pivots(i, new_pivots)
        cev = self.candles.update(i)
        ev += cev
        ev += self.liquidity.on_signatures(i, cev)
        ev += self.ranges.on_events(i, ev)
        if self.setups is not None:
            ev += self.setups.on_events(i, ev)
        # 4. marqueurs
        if self.imbalance is not None:
            ev += self.imbalance.update(i)
        if self.sessions is not None:
            ev += self.sessions.update(i)
        if self.month is not None:
            ev += self.month.update(i)
        for e in ev:
            if e.confirm_index != i:
                raise AssertionError(f"événement {e.kind} confirmé à {e.confirm_index} émis à {i}")
        self.log.extend(ev)
        return ev

    def run(self, bars: Iterable[Bar]) -> list[Event]:
        for b in bars:
            self.on_bar(b)
        return self.log

    def snapshot(self) -> dict:
        """État courant (après la dernière bougie close), pour le multi-UT."""
        return {"index": self.ctx.last, "structure": self.structure.snapshot()}
