from smv import Config, Engine
from smv.data import from_closes, from_ohlc

# Série de référence (pivots n = 1). Détail du calcul attendu : tests/test_structure.py.
CLOSES_UP_THEN_DOWN = [10, 11, 12, 11, 10, 11, 12.5, 13, 12, 11.5, 12, 14, 13, 12.2, 11, 10, 9]


def run(bars, **cfg):
    e = Engine(Config(**cfg))
    log = e.run(bars)
    return e, log


def kinds(log, kind):
    return [e for e in log if e.kind == kind]


__all__ = ["run", "kinds", "from_closes", "from_ohlc", "CLOSES_UP_THEN_DOWN"]
