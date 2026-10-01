import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
DS = os.environ.get("SMV_DS", "/tmp/ds")  # dossier des jeux de setups (setup_dataset.py / gen.py)
import sys, json, math; sys.path.insert(0,HERE)
from hyp import h2
from holdout import load
O=["GBPUSD","AUDUSD","USDCAD","USDCHF","EURGBP","EURCHF","USDJPY","EURJPY","GBPJPY","AUDJPY"]
def st(rs, key="r_net"):
    c=[r for r in rs if r["status"]=="closed"]; n=len(c); m=sum(r[key] for r in c)/n
    sd=math.sqrt(sum((r[key]-m)**2 for r in c)/(n-1)); return f"n={n} {key}={m:+.3f}±{1.96*sd/math.sqrt(n):.3f}"
B=[r for s in O for r in load(s,"base")]; S=[r for s in O for r in load(s,"schema")]
print("base        ", st(B), st(B,"r"))
print("schema      ", st(S), st(S,"r"))
print("H2 seul     ", st([r for r in B if h2(r)]), st([r for r in B if h2(r)],"r"))
print("schema+H2   ", st([r for r in S if h2(r)]), st([r for r in S if h2(r)],"r"))
C=[r for r in S if h2(r)]
for t in ("GOLDEN","CONCEPT"): print("  cand",t, st([r for r in C if r["type"]==t]))
