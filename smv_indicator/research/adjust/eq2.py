import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
DS = os.environ.get("SMV_DS", "/tmp/ds")  # dossier des jeux de setups (setup_dataset.py / gen.py)
import sys, json; sys.path.insert(0,HERE)
from hyp import h2
def load(sym, tag):
    fn=f"{DS}/{sym}.jsonl" if tag=="base" else f"{DS}/{sym}.{tag}.jsonl"
    return [r for r in map(json.loads, open(fn)) if r["status"]=="closed"]
def eq(rs):
    rs=sorted(rs,key=lambda r:r["closed"]); e=500; pk=500; dd=0
    for r in rs: e+=r["r_net"]*0.01*e; pk=max(pk,e); dd=max(dd,(pk-e)/pk)
    return e, dd, len(rs)
for s in ["EURUSD","XAUUSD","GBPUSD","AUDUSD","USDCAD","USDCHF","EURGBP","EURCHF","USDJPY","EURJPY","GBPJPY","AUDJPY"]:
    b=eq(load(s,"base")); c=eq([r for r in load(s,"schema") if h2(r)])
    print(f"{s}: base {b[0]:6.0f}$ ({b[2]} trades, DD {100*b[1]:.0f}%)  ->  ajusté {c[0]:6.0f}$ ({c[2]} trades, DD {100*c[1]:.0f}%)")
