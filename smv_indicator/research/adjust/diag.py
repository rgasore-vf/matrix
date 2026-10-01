import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
DS = os.environ.get("SMV_DS", "/tmp/ds")  # dossier des jeux de setups (setup_dataset.py / gen.py)
import json, math, sys
from collections import defaultdict
def rows(syms, y0, y1):
    out=[]
    for s in syms:
        for l in open(f"{DS}/{s}.jsonl"):
            r=json.loads(l)
            if y0<=r["year"]<=y1: out.append(r)
    return out
def summ(rs):
    c=[r for r in rs if r["status"]=="closed"]
    n=len(c)
    if n==0: return "n=0"
    m=sum(r["r_net"] for r in c)/n
    sd=math.sqrt(sum((r["r_net"]-m)**2 for r in c)/max(1,n-1))
    w=sum(r["r"]>0 for r in c)/n
    be=sum(1/(1+r["rr1"]) for r in c)/n
    return f"n={n:4d} win={w:.2f} null={be:.2f} Rnet={m:+.3f}±{1.96*sd/math.sqrt(n):.3f} tot={m*n:+.0f}"
if __name__=="__main__":
    D=rows(["EURUSD","XAUUSD"],2012,2018)
    print("ALL", summ(D))
    def by(key, f):
        g=defaultdict(list)
        for r in D: g[f(r)].append(r)
        print("--",key)
        for k in sorted(g, key=str): print(f"  {str(k):14s}", summ(g[k]))
    by("type",lambda r:r["type"])
    by("ltf aligned",lambda r:r["ltf_trend"]==r["dir"])
    by("htf aligned",lambda r:r["htf_trend"]==r["dir"])
    by("in_htf_zone",lambda r:r["in_htf_zone"])
    by("pd (buy disc / sell prem)",lambda r:None if r["htf_pd"] is None else ("good" if (r["dir"]==1 and r["htf_pd"]<0.5) or (r["dir"]==-1 and r["htf_pd"]>0.5) else "bad"))
    by("session",lambda r:r["session"])
    by("rr1",lambda r:"<1" if r["rr1"]<1 else "1-2" if r["rr1"]<2 else "2-4" if r["rr1"]<4 else ">=4")
    by("risk_atr",lambda r:"<1" if r["risk_atr"]<1 else "1-1.5" if r["risk_atr"]<1.5 else "1.5-2" if r["risk_atr"]<2 else ">=2")
    by("label",lambda r:r["label"].split("+")[0])
    by("dow",lambda r:r["dow"])
    c=[r for r in D if r["status"]=="closed"]
    losers=[r for r in c if r["r"]<0]
    for th in (0.5,1,1.5,2):
        print(f"losers with MFE>={th}R: {sum(r['mfe_r']>=th for r in losers)/len(losers):.2f}", f"all MFE>={th}: {sum(r['mfe_r']>=th for r in c)/len(c):.2f}")
    print("status", {k:sum(1 for r in D if r['status']==k) for k in set(r['status'] for r in D)})
