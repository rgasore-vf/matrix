"""Outil de parité MT5 : le comparateur, la lecture des fichiers et la reconstruction de la
configuration sont testés en simulant un export MT5 à partir du moteur Python.

Ce test NE valide PAS le code MQL5 (pas de compilateur MetaTrader dans cet environnement) ;
il garantit que l'outil qui servira à le valider lit correctement le format et détecte une
divergence d'une seule valeur.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

import mt5_parity as mp  # noqa: E402

from smv import Config, Engine  # noqa: E402
from smv.data import synthetic  # noqa: E402


def fake_export(tmp_path, cfg, bars, log, mutate=None):
    base = str(tmp_path / "SYM_M15")
    with open(base + "_bars.tsv", "w") as f:
        f.write("index\tt_open_utc\tt_close_utc\tt_srv\topen\thigh\tlow\tclose\n")
        for b in bars:
            f.write(f"{b.index}\t{int(b.t_open.timestamp())}\t{int(b.t_close.timestamp())}\tx\t"
                    f"{b.open:.17g}\t{b.high:.17g}\t{b.low:.17g}\t{b.close:.17g}\n")
    hdr = []
    for name in ("pivot_left", "pivot_right", "major_mode", "bm_body_min", "bm_range_atr", "zones_on",
                 "enable_setups", "enable_sessions", "session_mode", "sl_max_atr"):
        hdr.append(f"{name}={mp.fmt_value(getattr(cfg, name))}")
    with open(base + "_events.tsv", "w") as f:
        f.write("#smv_mt5 test\n#config " + ";".join(hdr) + "\n")
        f.write("kind\tconfirm\tanchor\tdir\tprice\tref\tdata\n")
        for k, e in enumerate(log):
            items = dict(e.data)
            if mutate is not None and k == mutate[0]:
                items[mutate[1]] = mutate[2]
            data = ";".join(f"{a}={mp.fmt_value(v)}" for a, v in items.items())
            f.write(f"{e.kind}\t{e.confirm_index}\t{e.anchor_index}\t{e.direction}\t{e.price:.15g}\t{e.ref}\t{data}\n")
    return base


def test_parity_tool_accepts_identical_journal(tmp_path, capsys):
    cfg = Config(pivot_left=3, pivot_right=3, enable_sessions=True)
    bars = synthetic(1500, seed=4)
    log = Engine(cfg).run(bars)
    base = fake_export(tmp_path, cfg, bars, log)
    assert mp.main([base, "--write-reference"]) == 0
    assert "PARITÉ" in capsys.readouterr().out
    assert os.path.exists(base + "_python.tsv")


def test_parity_tool_detects_one_changed_value(tmp_path, capsys):
    cfg = Config()
    bars = synthetic(1500, seed=4)
    log = Engine(cfg).run(bars)
    k = next(i for i, e in enumerate(log) if e.kind == "ZONE")
    base = fake_export(tmp_path, cfg, bars, log, mutate=(k, "distal", 123.0))
    assert mp.main([base]) == 1
    assert "[distal]" in capsys.readouterr().out


def test_config_header_types():
    cfg = mp.config_from_header({"pivot_left": "3", "major_mode": "B", "bm_range_atr": "",
                                 "enable_setups": "false", "eq_tol_atr": "0.2"})
    assert cfg.pivot_left == 3 and cfg.major_mode == "B" and cfg.bm_range_atr is None
    assert cfg.enable_setups is False and cfg.eq_tol_atr == 0.2
