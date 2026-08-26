# Moneyline: market calibration + own all-season pre-game features.
import pandas as pd, numpy as np, math, json, os
from collections import defaultdict, deque
D=os.path.dirname(os.path.abspath("outputs/gm/x"))
d=pd.read_csv("outputs/gm/gm_dataset.csv")
d=d.dropna(subset=["ml_h","ml_a","home_won"]).copy()
d["p_raw_h"]=1/d.ml_h; d["p_raw_a"]=1/d.ml_a
d["orr"]=d.p_raw_h+d.p_raw_a
d["p_mkt"]=d.p_raw_h/d.orr
d=d.sort_values(["date","game_id"]).reset_index(drop=True)
print("n priced ML:",len(d), "seasons:", sorted(d.season.unique()))

# ---------- 1. CALIBRATION ----------
def wilson(k,n):
    if n==0: return (0,0)
    z=1.96; p=k/n; den=1+z*z/n
    c=(p+z*z/(2*n))/den; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return (c-h,c+h)
bins=[0,.35,.45,.5,.55,.6,.65,.7,.75,.8,1.01]
d["bk"]=pd.cut(d.p_mkt,bins,right=False)
print("\n=== RELIABILITY TABLE: de-vigged closing home prob vs realised ===")
print(f"{'bucket':>16} {'n':>5} {'mean_p':>7} {'win%':>7} {'diff':>7} {'wilson95':>18} {'ROI_home%':>9}")
rows=[]
for b,g in d.groupby("bk",observed=True):
    n=len(g); w=g.home_won.sum(); mp=g.p_mkt.mean(); wr=w/n
    lo,hi=wilson(w,n)
    roi=(g.home_won*(g.ml_h-1)-(1-g.home_won)).mean()*100
    print(f"{str(b):>16} {n:>5} {mp:>7.3f} {wr:>7.3f} {wr-mp:>+7.3f} [{lo:>6.3f},{hi:>6.3f}] {roi:>+9.2f}")
    rows.append(dict(bucket=str(b),n=n,mean_p=mp,win=wr,diff=wr-mp,roi=roi))
# global calibration tests
from scipy import stats
obs=d.home_won.values; p=d.p_mkt.values
# Hosmer-Lemeshow style chi2 on 10 equal-count deciles
dec=pd.qcut(d.p_mkt,10,labels=False,duplicates="drop")
hl=0; k=0
print("\n--- decile version (equal count) ---")
for i in sorted(set(dec)):
    m=dec==i; n=m.sum(); e=p[m].sum(); o=obs[m].sum()
    hl+=(o-e)**2/(e*(1-p[m].mean())+1e-9); k+=1
    lo,hi=wilson(int(o),int(n))
    print(f"dec{i} n={n:4d} mean_p={p[m].mean():.3f} win={o/n:.3f} diff={o/n-p[m].mean():+.3f} [{lo:.3f},{hi:.3f}]")
pv=1-stats.chi2.cdf(hl,k-2)
print(f"Hosmer-Lemeshow chi2={hl:.2f} df={k-2} p={pv:.3f}")
# logistic recalibration: logit(p) coefficient should be 1, intercept 0
import statsmodels.api as sm
X=sm.add_constant(np.log(p/(1-p)))
res=sm.Logit(obs,X).fit(disp=0)
print("Recalibration logit: intercept=%.4f (se %.4f, t=%.2f) slope=%.4f (se %.4f, t vs 1 = %.2f)"%(
  res.params[0],res.bse[0],res.params[0]/res.bse[0],res.params[1],res.bse[1],(res.params[1]-1)/res.bse[1]))
print("Market Brier=%.5f  LogLoss=%.5f"%(np.mean((p-obs)**2), -np.mean(obs*np.log(p)+(1-obs)*np.log(1-p))))
print("Base-rate Brier=%.5f"%np.mean((obs.mean()-obs)**2))
d.to_csv("outputs/gm/gm_ml_base.csv",index=False)
