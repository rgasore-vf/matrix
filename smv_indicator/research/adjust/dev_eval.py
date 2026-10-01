import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
DS = os.environ.get("SMV_DS", "/tmp/ds")  # dossier des jeux de setups (setup_dataset.py / gen.py)
import sys, json; sys.path.insert(0,HERE)
from diag import summ
from hyp import h2
def load(sym, tag, y0, y1):
    fn=f"{DS}/{sym}.jsonl" if tag=="base" else f"{DS}/{sym}.{tag}.jsonl"
    return [r for r in map(json.loads, open(fn)) if y0<=r["year"]<=y1]
for tag in ("base","schema","be","schema_be"):
    for filt in ("-","H2"):
        rs=[r for s in ("EURUSD","XAUUSD") for r in load(s,tag,2012,2018) if filt=="-" or h2(r)]
        print(f"{tag:10s} {filt:3s}", summ(rs), "| EU", summ([r for r in rs if r["symbol"]=="EURUSD"]).split(" tot")[0].split("Rnet=")[1], "| XAU", summ([r for r in rs if r["symbol"]=="XAUUSD"]).split(" tot")[0].split("Rnet=")[1])
