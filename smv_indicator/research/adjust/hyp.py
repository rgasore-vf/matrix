import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
DS = os.environ.get("SMV_DS", "/tmp/ds")  # dossier des jeux de setups (setup_dataset.py / gen.py)
import sys; sys.path.insert(0,HERE)
from diag import rows, summ
SCHEMA={"STB","SPRING","UT","UTAD"}
def h1(r): return r["type"]=="CONCEPT" or r["label"].split("+")[0] in SCHEMA
def h2(r): return r["htf_pd"] is not None and ((r["dir"]==1 and r["htf_pd"]<0.5) or (r["dir"]==-1 and r["htf_pd"]>0.5))
D=rows(["EURUSD","XAUUSD"],2012,2018)
for name,f in [("base",lambda r:True),("H1",h1),("H2",h2),("H1+H2",lambda r:h1(r) and h2(r))]:
    print(f"{name:7s}", summ([r for r in D if f(r)]))
    for s in ("EURUSD","XAUUSD"): print("   ",s, summ([r for r in D if f(r) and r["symbol"]==s]))
