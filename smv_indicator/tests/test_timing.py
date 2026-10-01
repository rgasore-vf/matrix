"""R-OU-01, R-OU-02 : heure de Paris, heures d'hiver/été, fenêtre mensuelle."""
from datetime import datetime, timedelta, timezone

from helpers import kinds

from smv import Bar, Config, Engine


def bars_utc(start, n, minutes):
    out = []
    t = start
    for i in range(n):
        out.append(Bar(i, t, t + timedelta(minutes=minutes), 1.0, 1.1, 0.9, 1.0))
        t += timedelta(minutes=minutes)
    return out


def sessions(log):
    return {(e.data["name"], e.data["start"][:16]) for e in kinds(log, "SESSION")}


def test_europe_session_winter_and_summer_repo_mode():
    cfg = Config(enable_sessions=True, session_mode="repo")
    w = Engine(cfg).run(bars_utc(datetime(2026, 1, 13, 7, 0, tzinfo=timezone.utc), 8, 15))
    assert ("EUROPE", "2026-01-13T09:00") in sessions(w)          # 08:00 UTC = 09:00 Paris (hiver)
    s = Engine(cfg).run(bars_utc(datetime(2026, 7, 14, 5, 0, tzinfo=timezone.utc), 8, 15))
    assert ("EUROPE", "2026-07-14T08:00") in sessions(s)          # 06:00 UTC = 08:00 Paris (été)


def test_us_session_during_transatlantic_dst_gap():
    # 2026-03-17 : heure d'été aux États-Unis, pas encore en France. Le dépôt donne 14 h (hiver)
    # à Paris ; l'ouverture new-yorkaise conventionnelle (13:00 UTC hiver) a lieu à 12:00 UTC,
    # soit 13 h à Paris. Le marqueur suit le dépôt (14 h) : écart documenté (RESEARCH §4).
    log = Engine(Config(enable_sessions=True, session_mode="repo")).run(
        bars_utc(datetime(2026, 3, 17, 11, 0, tzinfo=timezone.utc), 16, 15))
    assert ("US", "2026-03-17T14:00") in sessions(log)


def test_measured_sessions_follow_home_time_zones():
    cfg = Config(enable_sessions=True)  # mode « measured »
    # hiver : Asie 10:00 JST = 02:00 Paris ; Europe 08:00 Londres = 09:00 Paris ; US 08:30 NY = 14:30
    w = Engine(cfg).run(bars_utc(datetime(2026, 1, 13, 0, 0, tzinfo=timezone.utc), 96, 15))
    got = sessions(w)
    assert {("ASIA", "2026-01-13T02:00"), ("EUROPE", "2026-01-13T09:00"),
            ("US_DATA", "2026-01-13T14:30"), ("US_10H", "2026-01-13T16:00")} <= got
    # été : Asie 03:00 Paris (le Japon ne change pas d'heure) ; Europe toujours 09:00 ; US 14:30
    s = Engine(cfg).run(bars_utc(datetime(2026, 7, 14, 0, 0, tzinfo=timezone.utc), 96, 15))
    got = sessions(s)
    assert {("ASIA", "2026-07-14T03:00"), ("EUROPE", "2026-07-14T09:00"),
            ("US_DATA", "2026-07-14T14:30"), ("US_10H", "2026-07-14T16:00")} <= got
    # semaine désynchronisée (heure d'été US seulement) : US à 13:30 Paris
    m = Engine(cfg).run(bars_utc(datetime(2026, 3, 17, 0, 0, tzinfo=timezone.utc), 96, 15))
    assert ("US_DATA", "2026-03-17T13:30") in sessions(m)


def test_month_window_extremes_confirmed_at_end_of_day_9():
    start = datetime(2026, 1, 20, 0, 0, tzinfo=timezone.utc)
    bars = []
    t = start
    for i in range(25):
        hi = 2.0 if t.day == 3 else 1.5
        lo = 0.5 if t.day == 28 else 1.0
        bars.append(Bar(i, t, t + timedelta(days=1), 1.2, hi, lo, 1.2))
        t += timedelta(days=1)
    log = Engine(Config(enable_sessions=True)).run(bars)
    mw = kinds(log, "MONTH_WINDOW")
    assert len(mw) == 1
    e = mw[0]
    assert e.data["month"] == "2026-02"
    assert bars[e.confirm_index].t_open.date().isoformat() == "2026-02-09"
    assert e.data["high"] == 2.0 and e.data["low"] == 0.5
