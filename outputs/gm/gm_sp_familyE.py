# FAMILY E (the last one): EV-gated bets from the beta-shrunk edge.
# GRID DECLARED: models {A_feats, B_elo, C_pooled(both, 2024-26)} x EV thresholds {0,2,4,6,8}% = 15 cells.
# NULL: market exactly calibrated. Ceiling computed BEFORE the real table.
import numpy as np, pandas as pd, os, pickle
from scipy.stats import norm
D=r"C:\Users\Axioo\wnba-line-capture"
rng=np.random.default_rng(53)
A=pd.read_csv(os.path.join(D,"outputs","gm","gm_model_rows.csv"))
P=pickle.load(open(os.path.join(D,"outputs","gm","gm_preds.pkl"),"rb"))
A["pred"]=P["('ridge a=300', 'margin', False)"]
B=pd.read_csv(os.path.join(D,"outputs","gm","gm_modelB_rows.csv")); B["pred"]=B.predB
def prep(df):
    g=df[df.pred.notna()&(df.ats!=0)].copy(); g["edge"]=g.pred-g.mkt; return g
Ap,Bp=prep(A),prep(B)
C=Ap[["game_id","season","date","spread","sp_h","sp_a","total","mkt","ats","edge","home_margin"]].merge(
    Bp[["game_id","edge"]],on="game_id",suffixes=("_a","_b"))
C["edge"]=(C.edge_a+C.edge_b)/2
SETS={"A_feats":Ap,"B_elo":Bp,"C_pooled":C}
def build(g):
    g=g.copy().sort_values(["season","date"]); g["shrunk"]=np.nan; g["sd_ats"]=np.nan
    for s in sorted(g.season.unique()):
        tr=g.season<s
        if tr.sum()<150: continue
        X=np.column_stack([np.ones(tr.sum()),g.loc[tr,"edge"].values])
        b=np.linalg.lstsq(X,g.loc[tr,"ats"].values,rcond=None)[0]
        sd=np.std(g.loc[tr,"ats"].values-X@b)
        te=g.season==s
        g.loc[te,"shrunk"]=b[0]+b[1]*g.loc[te,"edge"].values; g.loc[te,"sd_ats"]=sd
    h=g[g.shrunk.notna()].copy()
    h["p_home"]=norm.cdf(h.shrunk/h.sd_ats)
    evh=h.p_home*h.sp_h-1; eva=(1-h.p_home)*h.sp_a-1
    h["bet_home"]=evh>eva; h["ev"]=np.maximum(evh,eva)
    h["odds"]=np.where(h.bet_home,h.sp_h,h.sp_a); h["opp"]=np.where(h.bet_home,h.sp_a,h.sp_h)
    h["win"]=np.where(h.bet_home,h.ats>0,h.ats<0)
    ih,io=1/h.odds,1/h.opp; h["fair"]=ih/(ih+io)
    return h
H={k:build(v) for k,v in SETS.items()}
cells=[]
for k,h in H.items():
    for T in (0.0,0.02,0.04,0.06,0.08):
        g=h[h.ev>=T]; cells.append((f"{k} EV>={T*100:.0f}%",g.win.values,g.odds.values,g.fair.values,g))
best=np.empty(4000)
for b in range(4000):
    mx=-99
    for lb,w,od,fp,_ in cells:
        if len(w)<40: continue
        r=np.where(rng.random(len(fp))<fp,od-1,-1).mean()*100
        if r>mx: mx=r
    best[b]=mx
p95=np.percentile(best,95)
print(f"FAMILY E: {len(cells)} cells. NOISE CEILING p50={np.percentile(best,50):+.2f}% p95={p95:+.2f}% p99={np.percentile(best,99):+.2f}%\n")
def bootci(w,od,B_=6000):
    n=len(w); pnl=np.where(w,od-1,-1); i=rng.integers(0,n,(B_,n)); r=pnl[i].mean(axis=1)*100
    return np.percentile(r,2.5),np.percentile(r,97.5)
print(f"{'cell':20}{'n':>6}{'hit%':>8}{'fair%':>8}{'ROI%':>9}  95% CI          seasons+/-")
for lb,w,od,fp,g in cells:
    if len(w)<25: continue
    roi=np.where(w,od-1,-1).mean()*100; lo,hi=bootci(w,od)
    sr=[(s,np.where(kk.win,kk.odds-1,-1).mean()*100) for s,kk in g.groupby("season") if len(kk)>=8]
    pos=sum(1 for _,r in sr if r>0)
    fl="  <<< CLEARS" if roi>p95 and len(w)>=40 else ""
    print(f"{lb:20}{len(w):>6}{w.mean()*100:>7.2f}%{fp.mean()*100:>7.2f}%{roi:>8.2f}%  [{lo:+6.2f},{hi:+6.2f}]  {pos}/{len(sr)} pos{fl}")
print(f"\nCleared ceiling: {sum(1 for lb,w,od,fp,g in cells if len(w)>=40 and np.where(w,od-1,-1).mean()*100>p95)}")
# strict walk-forward season table for C_pooled EV>=6
for k in ("A_feats","B_elo","C_pooled"):
    g=H[k]; g=g[g.ev>=0.06]
    print(f"\n{k} EV>=6% by season:")
    for s,kk in g.groupby("season"):
        roi=np.where(kk.win,kk.odds-1,-1).mean()*100
        print(f"   {s} n={len(kk):3d} hit={kk.win.mean()*100:5.1f}% ROI={roi:+7.2f}%")
