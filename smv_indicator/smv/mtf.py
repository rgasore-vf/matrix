"""R-MTF-01 à R-MTF-03 : agrégation causale et lecture de l'UT supérieure.

Une bougie d'UT supérieure n'est publiée qu'une fois close. Un moteur d'UT basse
ne lit l'UT haute qu'à travers `HtfView.at(t)`, qui ne renvoie que l'état connu
au temps t (dernière bougie haute dont t_close <= t).
"""
from __future__ import annotations

from bisect import bisect_right
from copy import deepcopy
from datetime import datetime, timedelta, timezone

from .config import Config
from .context import validate_bar
from .engine import Engine
from .types import BEAR, BULL, Bar, Event, Kind


def resample(bars: list[Bar], minutes: int, origin: datetime | None = None) -> list[Bar]:
    """Agrège des bougies en UT de `minutes`, alignées sur `origin` (défaut : 1970-01-01 UTC).

    Only fully covered, contiguous intervals are emitted. A source candle straddling
    a target boundary is rejected: its OHLC cannot be split without finer data.
    """
    if type(minutes) is not int or minutes < 1:
        raise ValueError("minutes doit être un entier >= 1")
    if not bars:
        return []
    origin = origin or datetime(1970, 1, 1, tzinfo=timezone.utc)
    if origin.utcoffset() is None:
        raise ValueError("origin doit porter un fuseau")
    origin = origin.astimezone(timezone.utc)
    step = timedelta(minutes=minutes)
    out: list[Bar] = []
    cur = None
    previous_close = None
    for b in bars:
        validate_bar(b)
        opened, closed = b.t_open.astimezone(timezone.utc), b.t_close.astimezone(timezone.utc)
        if previous_close is not None and opened < previous_close:
            raise ValueError("bougies dupliquées ou chevauchantes")
        previous_close = closed
        k = (opened - origin) // step
        start = origin + k * step
        if closed > start + step:
            raise ValueError("une bougie source chevauche une borne de l'UT cible")
        if cur is None or cur["start"] != start:
            if cur is not None and cur["complete"] and cur["last_close"] == cur["start"] + step:
                out.append(_mk(len(out), cur, step))
            cur = {"start": start, "o": b.open, "h": b.high, "l": b.low, "c": b.close,
                   "v": b.volume, "last_close": closed, "complete": opened == start}
        else:
            cur["complete"] = cur["complete"] and opened == cur["last_close"]
            cur["h"] = max(cur["h"], b.high)
            cur["l"] = min(cur["l"], b.low)
            cur["c"] = b.close
            cur["v"] += b.volume
            cur["last_close"] = closed
    if cur is not None and cur["complete"] and cur["last_close"] == cur["start"] + step:
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
            self.times.append(b.t_close.astimezone(timezone.utc))
            self.states.append(self.engine.snapshot())

    def at(self, t: datetime) -> dict | None:
        """État de l'UT haute connu à l'instant t (None si aucune bougie haute close)."""
        if t.utcoffset() is None:
            raise ValueError("t doit porter un fuseau")
        k = bisect_right(self.times, t.astimezone(timezone.utc)) - 1
        return deepcopy(self.states[k]) if k >= 0 else None


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


def premium_discount_ok(htf_state: dict | None, entry: float, direction: int) -> bool:
    """Filtre premium/discount (CALIBRATION §7, définition externe ICT, RESEARCH §8.4).

    Position de l'entrée dans la jambe de l'UT haute, du niveau protégé à l'extrême courant :
    un achat passe sous 50 % (discount), une vente au-dessus (premium). Sans tendance, niveau
    protégé ou extrême connus, le filtre refuse : il n'invente pas de contexte."""
    if htf_state is None:
        return False
    s = htf_state["structure"] if "structure" in htf_state else htf_state
    if s["trend"] == 0 or s["prot"] is None or s["leg_ext"] is None:
        return False
    lo, hi = sorted((s["prot"][0], s["leg_ext"][0]))
    if hi <= lo:
        return False
    pd = (entry - lo) / (hi - lo)
    return pd < 0.5 if direction == BULL else pd > 0.5
