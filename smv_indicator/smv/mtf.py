"""R-MTF-01 à R-MTF-03 : agrégation causale et lecture de l'UT supérieure.

Une bougie d'UT supérieure n'est publiée qu'une fois close. Un moteur d'UT basse
ne lit l'UT haute qu'à travers `HtfView.at(t)`, qui ne renvoie que l'état connu
au temps t (dernière bougie haute dont t_close <= t).
"""
from __future__ import annotations

from bisect import bisect_right
from datetime import datetime, timedelta, timezone

from .config import Config
from .engine import Engine
from .types import BEAR, BULL, Bar, Event, Kind


def resample(bars: list[Bar], minutes: int, origin: datetime | None = None) -> list[Bar]:
    """Agrège des bougies en UT de `minutes`, alignées sur `origin` (défaut : 1970-01-01 UTC).

    Une bougie haute est émise seulement si la dernière bougie basse de sa période est
    présente (t_close basse >= t_close haute) ; la dernière période incomplète est omise.
    """
    if not bars:
        return []
    origin = origin or datetime(1970, 1, 1, tzinfo=bars[0].t_open.tzinfo or timezone.utc)
    step = timedelta(minutes=minutes)
    out: list[Bar] = []
    cur = None
    for b in bars:
        k = (b.t_open - origin) // step
        start = origin + k * step
        if cur is None or cur["start"] != start:
            if cur is not None and cur["last_close"] >= cur["start"] + step:
                out.append(_mk(len(out), cur, step))
            cur = {"start": start, "o": b.open, "h": b.high, "l": b.low, "c": b.close,
                   "v": b.volume, "last_close": b.t_close}
        else:
            cur["h"] = max(cur["h"], b.high)
            cur["l"] = min(cur["l"], b.low)
            cur["c"] = b.close
            cur["v"] += b.volume
            cur["last_close"] = b.t_close
    if cur is not None and cur["last_close"] >= cur["start"] + step:
        out.append(_mk(len(out), cur, step))
    return out


def _mk(index: int, cur: dict, step: timedelta) -> Bar:
    return Bar(index, cur["start"], cur["start"] + step, cur["o"], cur["h"], cur["l"], cur["c"], cur["v"])


class HtfView:
    """Exécute un moteur sur l'UT haute et expose son état daté par la clôture des bougies."""

    def __init__(self, htf_bars: list[Bar], cfg: Config | None = None) -> None:
        self.engine = Engine(cfg)
        self.times: list[datetime] = []
        self.states: list[dict] = []
        self.events: list[Event] = []
        for b in htf_bars:
            self.events += self.engine.on_bar(b)
            self.times.append(b.t_close)
            self.states.append(self.engine.snapshot())

    def at(self, t: datetime) -> dict | None:
        """État de l'UT haute connu à l'instant t (None si aucune bougie haute close)."""
        k = bisect_right(self.times, t) - 1
        return self.states[k] if k >= 0 else None


def bos_trap_risk(ltf_event: Event, htf_state: dict | None) -> bool:
    """R-MTF-03 (PROPOSITION) : BOS de continuation de l'UT basse contraire au biais de
    l'UT haute et dont le niveau reste en deçà du niveau protégé de l'UT haute."""
    if ltf_event.kind != Kind.BOS_CONTINUATION or htf_state is None:
        return False
    s = htf_state["structure"]
    if s["trend"] == 0 or s["prot"] is None or ltf_event.direction == s["trend"]:
        return False
    prot = s["prot"][0]
    if ltf_event.direction == BULL and s["trend"] == BEAR:
        return ltf_event.price < prot
    if ltf_event.direction == BEAR and s["trend"] == BULL:
        return ltf_event.price > prot
    return False
