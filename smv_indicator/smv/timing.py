"""R-OU-01 (heures de tir) et R-OU-02 (fenêtre du high/low du mois), heure de Paris.

Ce sont des MARQUEURS, pas des filtres : le dépôt dit « on peut trader avant comme après ».
Les bougies doivent porter des horodatages avec fuseau (UTC recommandé).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .config import SESSIONS_MEASURED, Config
from .context import Context
from .types import NONE, Event, Kind


def _is_summer(local: datetime) -> bool:
    off = local.utcoffset()
    std = local.tzinfo.utcoffset(datetime(local.year, 1, 15, 12)) if local.tzinfo else None
    return off is not None and std is not None and off > std


class SessionMarker:
    """Marque la bougie qui contient le début de chaque heure de tir.

    Mode « measured » (défaut) : ancrages mesurés dans le fuseau de chaque place
    (config.SESSIONS_MEASURED, CALIBRATION.md §5). Mode « repo » : heures de France du dépôt,
    hiver / été (config.SESSIONS_REPO), conservées pour comparaison."""

    def __init__(self, cfg: Config, ctx: Context) -> None:
        self.cfg = cfg
        self.ctx = ctx
        self.tz = ZoneInfo(cfg.timezone)
        self.anchor_tz = {name: ZoneInfo(tzname) for name, tzname, _, _ in SESSIONS_MEASURED}

    def _starts(self, day) -> list[tuple[str, datetime]]:
        out = []
        if self.cfg.session_mode == "measured":
            for name, _, h, m in SESSIONS_MEASURED:
                tz = self.anchor_tz[name]
                out.append((name, datetime(day.year, day.month, day.day, h, m, tzinfo=tz)))
        else:
            for name, h_winter, h_summer in self.cfg.sessions:
                probe = datetime(day.year, day.month, day.day, 12, tzinfo=self.tz)
                h = h_summer if _is_summer(probe) else h_winter
                out.append((name, datetime(day.year, day.month, day.day, h, tzinfo=self.tz)))
        return out

    def update(self, i: int) -> list[Event]:
        bar = self.ctx.bars[i]
        if bar.t_open.tzinfo is None:
            raise ValueError("les sessions exigent des horodatages avec fuseau")
        a, b = bar.t_open, bar.t_close
        out: list[Event] = []
        day = (a - timedelta(days=1)).date()
        while day <= (b + timedelta(days=1)).date():
            for name, start in self._starts(day):
                if a <= start < b:
                    end = start + timedelta(minutes=self.cfg.session_window_min)
                    loc = start.astimezone(self.tz)
                    out.append(Event(
                        Kind.SESSION, i, i, NONE, bar.open, f"SES:{name}:{start.isoformat()}",
                        {"name": name, "start": loc.isoformat(), "end": end.astimezone(self.tz).isoformat(),
                         "mode": self.cfg.session_mode},
                    ))
            day += timedelta(days=1)
        out.sort(key=lambda e: e.data["start"])
        return out


class MonthWindow:
    """Extrêmes de la fenêtre [26 du mois précédent 00:00, 10 du mois 00:00) heure de Paris.

    Confirmés à la clôture de la première bougie dont la clôture atteint la fin de fenêtre.
    Aucun biais n'est déduit (STRATEGY_SPEC R-OU-02, question Q-09).
    """

    def __init__(self, cfg: Config, ctx: Context) -> None:
        self.cfg = cfg
        self.ctx = ctx
        self.tz = ZoneInfo(cfg.timezone)
        self.state: dict[tuple[int, int], dict] = {}

    def _window_for(self, local: datetime) -> tuple[int, int] | None:
        """Mois (année, mois) dont la fenêtre contient l'instant local, sinon None."""
        if local.day >= 26:
            y, m = (local.year + 1, 1) if local.month == 12 else (local.year, local.month + 1)
            return (y, m)
        if local.day <= 9:
            return (local.year, local.month)
        return None

    def _end(self, key: tuple[int, int]) -> datetime:
        return datetime(key[0], key[1], 10, 0, tzinfo=self.tz)

    def update(self, i: int) -> list[Event]:
        bar = self.ctx.bars[i]
        if bar.t_open.tzinfo is None:
            raise ValueError("la fenêtre mensuelle exige des horodatages avec fuseau")
        a = bar.t_open.astimezone(self.tz)
        b = bar.t_close.astimezone(self.tz)
        out: list[Event] = []
        key = self._window_for(a)
        if key is not None:
            st = self.state.setdefault(key, {"high": None, "low": None, "done": False})
            if st["high"] is None or bar.high > st["high"][0]:
                st["high"] = (bar.high, i)
            if st["low"] is None or bar.low < st["low"][0]:
                st["low"] = (bar.low, i)
        for k, st in self.state.items():
            if not st["done"] and st["high"] is not None and b >= self._end(k):
                st["done"] = True
                out.append(Event(
                    Kind.MONTH_WINDOW, i, min(st["high"][1], st["low"][1]), NONE, st["high"][0],
                    f"MW:{k[0]}-{k[1]:02d}",
                    {"month": f"{k[0]}-{k[1]:02d}", "high": st["high"][0], "high_index": st["high"][1],
                     "low": st["low"][0], "low_index": st["low"][1]},
                ))
        return out


class ImbalanceScanner:
    """Fair value gap ICT à 3 bougies (définition EXTERNE, RESEARCH §2.6), confirmé à la 3e bougie."""

    def __init__(self, cfg: Config, ctx: Context) -> None:
        self.ctx = ctx

    def update(self, i: int) -> list[Event]:
        if i < 2:
            return []
        b0, b2 = self.ctx.bars[i - 2], self.ctx.bars[i]
        if b0.high < b2.low:
            return [Event(Kind.IMBALANCE, i, i - 1, 1, b2.low, f"IMB:{i - 1}",
                          {"top": b2.low, "bottom": b0.high, "definition": "ICT-3-candles"})]
        if b0.low > b2.high:
            return [Event(Kind.IMBALANCE, i, i - 1, -1, b2.high, f"IMB:{i - 1}",
                          {"top": b0.low, "bottom": b2.high, "definition": "ICT-3-candles"})]
        return []
