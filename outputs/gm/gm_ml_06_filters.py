import pandas as pd, numpy as np, warnings, itertools
warnings.filterwarnings("ignore")
rng=np.random.default_rng(3)
p=pd.read_csv("outputs/gm/gm_preds.csv")
d=pd.read_csv("outputs/gm/gm_ml_base.csv")
p=p.merge(d[["game_id","home","away","home_margin"]],on="game_id",how="left")
pm=p.p_mkt.values; mlh=p.ml_h.values; mla=p.ml_a.values; y=p.y.values
elo=p.o_elo.values
# elo-implied prob vs market (disagreement)
pe=1/(1+10**(-(elo+80)/400))
dis=pe-pm
# --- DECLARE THE GRID ---
SIDES={"home":(np.ones(len(p),bool),True),"away":(np.ones(len(p),bool),False)}
FILTERS={}
FILTERS["all"]=np.ones(len(p),bool)
for lo,hi in [(0,.35),(.35,.45),(.45,.55),(.55,.65),(.65,.8),(.8,1.01)]:
    FILTERS[f"pmkt[{lo},{hi})"]=(pm>=lo)&(pm<hi)
FILTERS["fav_home"]=pm>0.5; FILTERS["fav_away"]=pm<0.5
FILTERS["b2b_home"]=p.o_b2bh.values==1; FILTERS["b2b_away"]=p.o_b2ba.values==1
FILTERS["no_b2b"]=(p.o_b2bh.values==0)&(p.o_b2ba.values==0)
FILTERS["rest_adv_home"]=p.o_rest.values>=2; FILTERS["rest_adv_away"]=p.o_rest.values<=-2
for S in sorted(p.season.unique()): FILTERS[f"season{S}"]=p.season.values==S
q=np.nanpercentile(dis,[25,50,75])
FILTERS["elo>mkt_Q4"]=dis>q[2]; FILTERS["elo<mkt_Q1"]=dis<q[0]
FILTERS["elo_dis>+.05"]=dis>0.05; FILTERS["elo_dis<-.05"]=dis<-0.05
NC=len(SIDES)*len(FILTERS)
print("DECLARED FILTER GRID: 2 sides x %d filters = %d cells (min n=60)"%(len(FILTERS),NC))
print("NULL: outcomes resampled Bernoulli(de-vigged closing prob); prices/filters fixed.")
def grid(yy,minn=60):
    out=[]
    for sname,(sm,ishome) in SIDES.items():
        for fname,fm in FILTERS.items():
            m=sm&fm&~np.isnan(pm)
            n=m.sum()
            if n<minn: continue
            pnl=(yy[m]*(mlh[m]-1)-(1-yy[m])) if ishome else ((1-yy[m])*(mla[m]-1)-yy[m])
            out.append((sname,fname,n,pnl.mean()*100,m,ishome))
    return out
b=[]
for it in range(3000):
    ys=(rng.random(len(p))<pm).astype(float)
    b.append(max(c[3] for c in grid(ys)))
b=np.array(b)
CEIL=np.percentile(b,95)
print("NOISE CEILING best-of-%d: p50=%.2f%% p95=%.2f%% p99=%.2f%%"%(len(grid(y)),np.percentile(b,50),CEIL,np.percentile(b,99)))
real=sorted(grid(y),key=lambda c:-c[3])
def boot(m,ishome,B=4000):
    pnl=(y[m]*(mlh[m]-1)-(1-y[m])) if ishome else ((1-y[m])*(mla[m]-1)-y[m])
    s=rng.integers(0,len(pnl),(B,len(pnl))); v=pnl[s].mean(1)*100
    return np.percentile(v,2.5),np.percentile(v,97.5)
print("\nTop-10 real filter cells:")
for sname,fname,n,roi,m,ih in real[:10]:
    lo,hi=boot(m,ih)
    print(f"  {sname:5} {fname:16} n={n:5} ROI={roi:+7.2f}% CI[{lo:+.1f},{hi:+.1f}] {'*ABOVE CEIL*' if roi>CEIL else ''}")
print("\nBottom-3:", [(c[0],c[1],c[2],round(c[3],2)) for c in real[-3:]])
print("\nVERDICT FILTER STAGE:", "ABOVE CEILING" if real[0][3]>CEIL else "BELOW NOISE CEILING - not a finding")

# ---- MECHANISM: does anything predict the market residual? ----
import statsmodels.api as sm
ml=np.log(pm/(1-pm))
Z={"o_elo/100":elo/100,"o_rest":p.o_rest.values,"o_b2bh":p.o_b2bh.values,"o_b2ba":p.o_b2ba.values,
   "o_form5":p.o_form5.values,"o_form10":p.o_form10.values,"elo_dis":dis}
print("\n=== MECHANISM: logit(P(home win)) = a + b*market_logit + c*z   (c should be 0 if close is efficient) ===")
for k,v in Z.items():
    ok=~np.isnan(v)&~np.isnan(ml)
    X=sm.add_constant(np.column_stack([ml[ok],v[ok]]))
    r=sm.Logit(y[ok],X).fit(disp=0)
    print(f"  z={k:10} c={r.params[2]:+.4f} se={r.bse[2]:.4f} t={r.params[2]/r.bse[2]:+.2f} p={r.pvalues[2]:.3f} n={ok.sum()}")
# joint
ok=~np.isnan(elo)
X=sm.add_constant(np.column_stack([ml[ok]]+[Z[k][ok] for k in ["o_elo/100","o_rest","o_b2bh","o_b2ba","o_form10"]]))
r=sm.Logit(y[ok],X).fit(disp=0)
print("  JOINT LR test vs market-only: chi2=%.2f df=5 p=%.3f"%(2*(r.llf-sm.Logit(y[ok],sm.add_constant(ml[ok])).fit(disp=0).llf),
      1-__import__("scipy.stats",fromlist=["x"]).chi2.cdf(2*(r.llf-sm.Logit(y[ok],sm.add_constant(ml[ok])).fit(disp=0).llf),5)))
# raw-outcome mechanism: margin residual vs rest/b2b
resid=p.home_margin.values+p.spread.values
for k,v in [("o_rest",p.o_rest.values),("o_b2bh",p.o_b2bh.values),("o_b2ba",p.o_b2ba.values),("elo_dis",dis)]:
    ok=~np.isnan(resid)&~np.isnan(v)
    c=np.corrcoef(v[ok],resid[ok])[0,1]; n=ok.sum(); t=c*np.sqrt(n-2)/np.sqrt(1-c*c)
    print(f"  RAW ATS-residual corr with {k:8}: r={c:+.4f} t={t:+.2f} n={n}")
