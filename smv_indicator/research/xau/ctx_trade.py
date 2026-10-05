"""Trade à l'échelle H4 dans le contexte « tendance H4 qui tient » (or) : première bougie du jour où le
contexte est vrai, entrée à l'ouverture suivante, stop 1 ATR H4, TP k ATR H4, horizon 48 h.
Contexte (lu sur les tables, voir docs/XAU_RESEARCH.md) : D1 dans le même sens que H4, ATR H4 <= 0,95 x
sa moyenne de 100 bougies, heure de Paris 6 h-14 h, amplitude du jour < 0,6 x la moyenne 20 jours."""
import sys, os
import numpy as np, pandas as pd
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.join(HERE,"..")); sys.path.insert(0,os.path.join(HERE,"..",".."))
from marketdata import load
from smv import Config, Engine
COST=0.35
def run(ctxfile, rule):
    c=pd.read_parquet(ctxfile); bars=load("XAUUSD","m15")
    O=np.array([b.open for b in bars]);H=np.array([b.high for b in bars]);L=np.array([b.low for b in bars]);C=np.array([b.close for b in bars])
    h4=load("XAUUSD","h4"); he=Engine(Config(enable_setups=False)); k=0; atr={}
    # ATR H4 connue à chaque bougie M15 de la matrice
    times=[b.t_close for b in bars]
    for b in bars:
        while k<len(h4) and h4[k].t_close<=b.t_close: he.on_bar(h4[k]); he.log.clear(); k+=1
        if k: atr[b.index]=he.ctx.atr[-1]
    c=c[rule(c)].copy(); c["day"]=[bars[i].t_open.date() for i in c.i]
    c=c.groupby("day").head(1)
    out=[]
    for r in c.itertuples():
        i=r.i; d=r.d; a=atr[i]; E=O[i+1]; S=E-d*a; res={"year":r.year,"d":d}
        for kk in (1,1.5,2,3):
            T=E+d*kk*a; R=None
            for j in range(i+1,min(len(bars),i+1+192)):
                if (L[j]<=S) if d==1 else (H[j]>=S): R=-1.0; break
                if (H[j]>=T) if d==1 else (L[j]<=T): R=float(kk); break
            if R is None: R=(C[min(len(bars)-1,i+192)]-E)*d/a
            res[f"r{kk:g}"]=R-COST/a
        out.append(res)
    return pd.DataFrame(out)
if __name__=="__main__":
    rule=lambda c:(c.d1_agree==1)&(c.volr4<=0.95)&c.hour.between(6,14)&(c.day_used<0.6)
    t=run(sys.argv[1],rule); t["per"]=np.where(t.year<=2017,"13-17",np.where(t.year<=2019,"18-19","20-22"))
    t=t[t.year>=2013]
    print(t.groupby("per")[["r1","r1.5","r2","r3"]].agg(["mean","count"]).round(3).to_string())
    print("par an (TP 2 ATR):",t.groupby("year")["r2"].mean().round(3).to_dict(), " trades/an:", round(len(t)/9.2,1))
    t.to_parquet(sys.argv[2])
