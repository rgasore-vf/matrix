"""R-CA-01 à R-CA-05 : classification des bougies.

Les seuils sont des PROPOSITIONS (le dépôt n'en donne aucun) ; voir config.PROVENANCE.
"""
from __future__ import annotations

from .config import Config
from .context import Context
from .types import BEAR, BULL, NONE, Bar, Event, Kind


def is_doji(bar: Bar, cfg: Config) -> bool:
    """R-CA-04 : corps <= doji_body_max x range. Une bougie sans range est un doji."""
    return bar.range == 0 or bar.body_ratio <= cfg.doji_body_max


def is_manipulative(bar: Bar, zone_dir: int, cfg: Config, atr_prev: float | None) -> bool:
    """R-CA-01 : bougie « pleine » de couleur opposée au départ de la zone.

    zone_dir = BULL pour une zone de demande (la BM est baissière), BEAR pour une offre.
    """
    if bar.color != -zone_dir:
        return False
    if bar.body_ratio < cfg.bm_body_min:
        return False
    if cfg.bm_range_atr is not None and atr_prev is not None:
        if bar.range < cfg.bm_range_atr * atr_prev:
            return False
    return True


def liquidity_signature(bar: Bar, cfg: Config) -> int:
    """R-CA-05 : mèche « derrière le corps » (dans le sens de la bougie).

    Retourne BULL si bougie haussière à longue mèche haute (cible au plus haut),
    BEAR si bougie baissière à longue mèche basse (cible au plus bas), NONE sinon.
    """
    if bar.range <= 0:
        return NONE
    if bar.color == BULL and (bar.high - bar.close) / bar.range >= cfg.liqsig_wick_min:
        return BULL
    if bar.color == BEAR and (bar.close - bar.low) / bar.range >= cfg.liqsig_wick_min:
        return BEAR
    return NONE


class CandleScanner:
    """Émet les signatures de liquidité à la clôture de chaque bougie."""

    def __init__(self, cfg: Config, ctx: Context) -> None:
        self.cfg = cfg
        self.ctx = ctx

    def update(self, i: int) -> list[Event]:
        bar = self.ctx.bars[i]
        sig = liquidity_signature(bar, self.cfg)
        if sig == NONE:
            return []
        price = bar.high if sig == BULL else bar.low
        return [Event(Kind.LIQ_SIGNATURE, i, i, sig, price, f"LS:{i}", {"side": "H" if sig == BULL else "L"})]
