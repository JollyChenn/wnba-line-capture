# DECISIVE TEST of the only surviving signal: beta(ats ~ edge) > 0.
# (a) permutation test on beta, (b) walk-forward BETA-SHRUNK edge -> implied cover prob ->
#     bet only when p_implied > breakeven, (c) does the ROI ever go positive OOS?
import numpy as np, pandas as pd, os, pickle
from scipy.stats import norm
D=r"C:\Users\Axioo\wnba-line-capture"
rng=np.random.default_rng(41)
A=pd.read_csv(os.path.join(D,"outputs","gm","gm_model_rows.csv"))
P=pickle.load(open(os.path.join(D,"outputs","gm","gm_preds.pkl"),"rb"))
A["pred"]=P["('ridge a=300', 'margin', False)"]
B=pd.read_csv(os.path.join(D,"outputs","gm","gm_modelB_rows.csv")); B["pred"]=B.predB
def prep(df):
    g=df[df.pred.notna()&(df.ats!=0)].copy(); g["edge"]=g.pred-g.mkt; return g.sort_values(["season","date"])
SETS={"A_feats(2024-26)":prep(A),"B_elo(2021-26)":prep(B)}

# (a) PERMUTATION TEST on beta: shuffle ats WITHIN season (kills any real edge-ats link,
#     keeps season-level ATS distribution). 5000 draws.
print("=== (a) permutation test on beta(ats ~ edge) ===")
for nm,g in SETS.items():
    x=g.edge.values; y=g.ats.values; s=g.season.values
    def beta(yy):
        X=np.column_stack([np.ones(len(x)),x]); return np.linalg.lstsq(X,yy,rcond=None)[0][1]
    b0=beta(y); null=np.empty(5000)
    for i in range(5000):
        yy=y.copy()
        for ss in np.unique(s):
            m=s==ss; yy[m]=rng.permutation(yy[m])
        null[i]=beta(yy)
    p=(null>=b0).mean()
    print(f"  {nm:20} beta={b0:+.4f}  perm p(one-sided)={p:.4f}  null p95={np.percentile(null,95):+.4f}")
    # sign test across seasons
    sg=[]
    for ss in sorted(np.unique(s)):
        m=s==ss; X=np.column_stack([np.ones(m.sum()),x[m]])
        sg.append(np.linalg.lstsq(X,y[m],rcond=None)[0][1])
    print(f"     per-season betas {[round(v,2) for v in sg]}  positive {sum(v>0 for v in sg)}/{len(sg)}  sign-test p={0.5**len(sg)*1:.4f}")

# (b) walk-forward beta-shrunk edge -> implied cover prob -> bet only if +EV
print("\n=== (b) walk-forward BETA-SHRUNK edge, bet only when implied p > 1/odds ===")
print(f"{'set':20}{'thresh(EV%)':>12}{'n':>6}{'hit%':>8}{'ROI%':>9}  95% CI      per-season ROI")
def bootci(w,od,B_=4000):
    n=len(w)
    if n<5: return (np.nan,np.nan)
    pnl=np.where(w,od-1,-1); i=rng.integers(0,n,(B_,n)); r=pnl[i].mean(axis=1)*100
    return np.percentile(r,2.5),np.percentile(r,97.5)
for nm,g in SETS.items():
    g=g.copy(); g["shrunk"]=np.nan
    seasons=sorted(g.season.unique())
    for si,s in enumerate(seasons):
        tr=g.season<s
        if tr.sum()<150: continue
        X=np.column_stack([np.ones(tr.sum()),g.loc[tr,"edge"].values])
        b=np.linalg.lstsq(X,g.loc[tr,"ats"].values,rcond=None)[0]
        sd=np.std(g.loc[tr,"ats"].values-X@b)
        te=g.season==s
        g.loc[te,"shrunk"]=b[0]+b[1]*g.loc[te,"edge"].values
        g.loc[te,"sd_ats"]=sd
    h=g[g.shrunk.notna()].copy()
    h["p_home"]=norm.cdf(h.shrunk/h.sd_ats)
    h["ev_home"]=h.p_home*h.sp_h-1; h["ev_away"]=(1-h.p_home)*h.sp_a-1
    h["bet_home"]=h.ev_home>h.ev_away
    h["ev"]=np.maximum(h.ev_home,h.ev_away)
    h["odds"]=np.where(h.bet_home,h.sp_h,h.sp_a)
    h["win"]=np.where(h.bet_home,h.ats>0,h.ats<0)
    for T in (0.00,0.02,0.04,0.06,0.08):
        k=h[h.ev>=T]
        if len(k)<20: continue
        roi=np.where(k.win,k.odds-1,-1).mean()*100; lo,hi=bootci(k.win.values,k.odds.values)
        ps=" ".join(f"{s}:{np.where(kk.win,kk.odds-1,-1).mean()*100:+5.1f}" for s,kk in k.groupby("season") if len(kk)>5)
        print(f"{nm:20}{T*100:>11.0f}%{len(k):>6}{k.win.mean()*100:>7.2f}%{roi:>8.2f}%  [{lo:+6.2f},{hi:+6.2f}]  {ps}")

# (c) how big would beta have to be to be profitable?  (theory, given vig)
print("\n=== (c) profitability requirement ===")
for nm,g in SETS.items():
    sd=g.ats.std(); es=g.edge.std()
    X=np.column_stack([np.ones(len(g)),g.edge.values]); b=np.linalg.lstsq(X,g.ats.values,rcond=None)[0][1]
    be=1/ (2/ (1/g.sp_h+1/g.sp_a) )   # avg de-vig breakeven ~ fair; use raw avg implied
    be_raw=(1/g.sp_h.mean()+0)  # simple
    need_pp=0.0263   # +2.63pp over 50% = the median 5.27% spread overround
    # bet the top-decile |edge|; expected true ATS shift:
    top=g[g.edge.abs()>=g.edge.abs().quantile(0.9)]
    shift=b*top.edge.abs().mean()
    got_pp=norm.cdf(shift/sd)-0.5
    print(f"  {nm:20} beta={b:+.3f} sd(ats)={sd:.2f} top-decile mean|edge|={top.edge.abs().mean():.2f}"
          f" -> true cover shift {got_pp*100:+.2f}pp vs {need_pp*100:.2f}pp needed"
          f"  => implied ROI {(0.5+got_pp)*(1+ (1/ (0.5+need_pp) -1))*100-100:+.2f}%")
    # beta needed
    need_shift=norm.ppf(0.5+need_pp)*sd
    print(f"     beta needed for breakeven at top decile = {need_shift/top.edge.abs().mean():.3f} (have {b:.3f})")
