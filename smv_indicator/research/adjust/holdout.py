import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
DS = os.environ.get("SMV_DS", "/tmp/ds")  # dossier des jeux de setups (setup_dataset.py / gen.py)
import sys, json; sys.path.insert(0,HERE)
from diag import summ
from hyp import h2
def load(sym, tag, y0=2000, y1=2100):
    fn=f"{DS}/{sym}.jsonl" if tag=="base" else f"{DS}/{sym}.{tag}.jsonl"
    return [r for r in map(json.loads, open(fn)) if y0<=r["year"]<=y1]
cand=lambda s,y0,y1: [r for r in load(s,"schema",y0,y1) if h2(r)]
print("== VALIDATION 1 : EURUSD/XAUUSD 2019-2022")
for s in ("EURUSD","XAUUSD"):
    print(f"  {s} base     ", summ(load(s,"base",2019,2022)))
    print(f"  {s} candidat ", summ(cand(s,2019,2022)))
print("  ensemble base    ", summ(load("EURUSD","base",2019,2022)+load("XAUUSD","base",2019,2022)))
print("  ensemble candidat", summ(cand("EURUSD",2019,2022)+cand("XAUUSD",2019,2022)))
print("== VALIDATION 2 : 10 paires jamais vues, 2012-2022")
O=["GBPUSD","AUDUSD","USDCAD","USDCHF","EURGBP","EURCHF","USDJPY","EURJPY","GBPJPY","AUDJPY"]
allb=[];allc=[]
for s in O:
    b=load(s,"base"); c=cand(s,2000,2100); allb+=b; allc+=c
    print(f"  {s} base {summ(b)}\n         cand {summ(c)}")
print("  TOTAL base    ", summ(allb)); print("  TOTAL candidat", summ(allc))
