"""Types de base du moteur SMV.

Conventions (STRATEGY_SPEC.md §0.4) :
- indices croissants avec le temps (0 = plus ancienne bougie) ;
- une bougie n'est jamais traitée avant sa clôture ;
- chaque événement porte `confirm_index` (bougie close qui le rend vrai)
  et `anchor_index` (bougie où il est dessiné), avec anchor_index <= confirm_index.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping

BULL = 1
BEAR = -1
NONE = 0


@dataclass(frozen=True)
class Bar:
    index: int
    t_open: datetime
    t_close: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

    @property
    def body(self) -> float:
        return abs(self.close - self.open)

    @property
    def range(self) -> float:
        return self.high - self.low

    @property
    def body_ratio(self) -> float:
        r = self.range
        return self.body / r if r > 0 else 0.0

    @property
    def color(self) -> int:
        if self.close > self.open:
            return BULL
        if self.close < self.open:
            return BEAR
        return NONE


class Kind:
    """Types d'événements. Les commentaires renvoient aux règles de la spécification."""

    PIVOT_HIGH = "PIVOT_HIGH"                # R-ST-02 / R-ST-03
    PIVOT_LOW = "PIVOT_LOW"
    TREND_INIT = "TREND_INIT"                # R-ST-04 (initialisation)
    BOS_CONTINUATION = "BOS_CONTINUATION"    # R-ST-06
    BOS_CHANGE = "BOS_CHANGE"                # R-ST-06 (BOS classique = CHoCH SMC)
    PROTECTED_SWEEP = "PROTECTED_SWEEP"      # R-ST-05 (mèche sans clôture au-delà du niveau protégé)
    FAIL = "FAIL"                            # R-ST-07 (changement de caractère SMV)
    INDUCEMENT = "INDUCEMENT"                # R-LQ-05
    LIQ_LEVEL = "LIQ_LEVEL"                  # R-LQ-01 (niveau créé, intact)
    LIQ_CLEAN = "LIQ_CLEAN"                  # R-LQ-01 (prise en mèche)
    LIQ_BOS = "LIQ_BOS"                      # R-LQ-01 (clôture au-delà)
    EQUAL_LEVELS = "EQUAL_LEVELS"            # R-LQ-03
    LIQ_SIGNATURE = "LIQ_SIGNATURE"          # R-CA-05
    ZONE = "ZONE"                            # R-OD-01
    ZONE_TOUCH = "ZONE_TOUCH"                # R-OD-03
    ZONE_BROKEN = "ZONE_BROKEN"              # R-OD-03
    ODF_LINK = "ODF_LINK"                    # R-OD-04
    BREAKER = "BREAKER"                      # R-OD-05
    BREAKER_REACTION = "BREAKER_REACTION"
    RANGE_OPEN = "RANGE_OPEN"                # R-CE-01
    RANGE_SWEEP = "RANGE_SWEEP"              # R-GS-02
    RANGE_INTENTION = "RANGE_INTENTION"      # R-CE-02
    CAUSE_COMPLETE = "CAUSE_COMPLETE"        # R-CE-02
    RANGE_EXIT = "RANGE_EXIT"                # R-CE-01 / R-GS-02
    IMBALANCE = "IMBALANCE"                  # §15 (définition externe, optionnelle)
    SETUP = "SETUP"                          # R-SE-01, §9 (setup créé, éventuellement rejeté)
    SETUP_TRIGGERED = "SETUP_TRIGGERED"      # R-SE-01 (entrée touchée)
    SETUP_CLOSED = "SETUP_CLOSED"            # R-SE-02 / R-SE-03 (stop ou cible)
    SETUP_EXPIRED = "SETUP_EXPIRED"          # R-SE-01 (délai dépassé ou retournement)
    SESSION = "SESSION"                      # R-OU-01
    MONTH_WINDOW = "MONTH_WINDOW"            # R-OU-02


@dataclass(frozen=True)
class Event:
    kind: str
    confirm_index: int
    anchor_index: int
    direction: int
    price: float
    ref: str
    data: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.anchor_index > self.confirm_index:
            raise ValueError(
                f"{self.kind} {self.ref}: anchor_index {self.anchor_index} "
                f"> confirm_index {self.confirm_index}"
            )

    def key(self) -> tuple:
        """Identité stable, utilisée par le test d'invariance par préfixe."""
        return (
            self.kind,
            self.confirm_index,
            self.anchor_index,
            self.direction,
            round(self.price, 10),
            self.ref,
            tuple(sorted((k, repr(v)) for k, v in self.data.items())),
        )
