# STEP 3+4: SpreadEdge = model_margin - market_margin.
# FAMILY B GRID (DECLARED BEFORE RESULTS):
#   models {A_ridge300_margin, A_enet_margin_mkt, B_elo} x thresholds {1,2,3,4,5}
#   x side-restriction {any, home-side-only, away-side-only}  = 3*5*3 = 45 cells
# FAMILY C GRID (DECLARED): best model @ threshold 2, split by
#   |spread| bucket(4) + side home/away(2) + fav/dog(2) + total tercile(3) + rest state(3)
#   + season(6 or 8) = 22-24 cells
# NULL for both: market exactly calibrated (win prob = de-vigged price of the side actually taken).
import numpy as np, pandas as pd, os, pickle
D=r"C:\Users\Axioo\wnba-line-capture"
rng=np.random.default_rng(23)
A=pd.read_csv(os.path.join(D,"outputs","gm","gm_model_rows.csv"))
P=pickle.load(open(os.path.join(D,"outputs","gm","gm_preds.pkl"),"rb"))
A["predA1"]=P["('ridge a=300', 'margin', False)"]; A["predA2"]=P["('enet a=1 l1=.5', 'margin', True)"]
B=pd.read_csv(os.path.join(D,"outputs","gm","gm_modelB_rows.csv"))
def prep(df,pcol):
    g=df[df[pcol].notna() & (df.ats!=0)].copy()
    g["edge"]=g[pcol]-g.mkt                      # + => home covers more than market thinks
    g["bet_home"]=g.edge>0
    g["odds"]=np.where(g.bet_home,g.sp_h,g.sp_a)
    g["opp"]=np.where(g.bet_home,g.sp_a,g.sp_h)
    g["win"]=np.where(g.bet_home, g.ats>0, g.ats<0)
    ih,ia=1/g.odds,1/g.opp; g["fair"]=ih/(ih+ia)
    return g
SETS={"A_ridge300(feats,2024-26)":prep(A,"predA1"),
      "A_enet+mkt(feats,2024-26)":prep(A,"predA2"),
      "B_elo(wide,2021-26)":prep(B,"predB")}
for k,v in SETS.items(): print(f"{k}: n={len(v)}  mean|edge|={v.edge.abs().mean():.2f}  sd={v.edge.std():.2f}")

def cellsB():
    out=[]
    for nm,g in SETS.items():
        for T in (1,2,3,4,5):
            m=g.edge.abs()>=T
            for sd_,mask in (("any",m),("homeside",m&g.bet_home),("awayside",m&~g.bet_home)):
                gg=g[mask]
                out.append((f"{nm} |e|>={T} {sd_}", gg.win.values, gg.odds.values, gg.fair.values))
    return out
C=cellsB()
def ceiling(C,minn=40,B_=4000):
    best=np.empty(B_)
    for b in range(B_):
        mx=-99
        for lb,w,od,fp in C:
            if len(w)<minn: continue
            r=np.where(rng.random(len(fp))<fp,od-1,-1).mean()*100
            if r>mx: mx=r
        best[b]=mx
    return best
bst=ceiling(C)
p95=np.percentile(bst,95)
print(f"\nFAMILY B: {len(C)} cells declared. NOISE CEILING best-cell ROI (cells n>=40): p50={np.percentile(bst,50):+.2f}% p95={p95:+.2f}% p99={np.percentile(bst,99):+.2f}%")
def bootci(w,od,B_=4000):
    n=len(w); pnl=np.where(w,od-1,-1); i=rng.integers(0,n,(B_,n)); r=pnl[i].mean(axis=1)*100
    return np.percentile(r,2.5),np.percentile(r,97.5)
print(f"\n{'cell':44} {'n':>5} {'hit%':>7} {'fair%':>7} {'ROI%':>8}  95% CI")
for lb,w,od,fp in C:
    if len(w)<40: continue
    roi=np.where(w,od-1,-1).mean()*100; lo,hi=bootci(w,od)
    fl=" <<< CLEARS" if roi>p95 else ""
    print(f"{lb:44} {len(w):5d} {w.mean()*100:6.2f}% {fp.mean()*100:6.2f}% {roi:+7.2f}%  [{lo:+6.2f},{hi:+6.2f}]{fl}")

# ---- per-season walk-forward for the |e|>=2 any cell of each model ----
print("\n--- per-season, |edge|>=2, any side ---")
for nm,g in SETS.items():
    gg=g[g.edge.abs()>=2]
    line=f"  {nm:28}"
    for s in sorted(gg.season.unique()):
        h=gg[gg.season==s]; roi=np.where(h.win,h.odds-1,-1).mean()*100
        line+=f" {s}:{roi:+6.1f}(n{len(h)})"
    print(line)

# ---- FAMILY C: filters on model B @ |e|>=2 (largest n) ----
g=SETS["B_elo(wide,2021-26)"]; g=g[g.edge.abs()>=2].copy()
print(f"\nFAMILY C: filters on B_elo |e|>=2 (n={len(g)})")
FC=[]
absp=g.spread.abs()
for nm,m in [("|sp|0.5-3.5",(absp<=3.5)),("|sp|4-7.5",(absp>3.5)&(absp<=7.5)),("|sp|8-11.5",(absp>7.5)&(absp<=11.5)),("|sp|12+",absp>11.5),
             ("bet HOME",g.bet_home),("bet AWAY",~g.bet_home),
             ("bet FAV",(g.bet_home&(g.spread<0))|((~g.bet_home)&(g.spread>0))),
             ("bet DOG",(g.bet_home&(g.spread>0))|((~g.bet_home)&(g.spread<0))),
             ("total low",g.total<=g.total.quantile(1/3)),("total mid",(g.total>g.total.quantile(1/3))&(g.total<=g.total.quantile(2/3))),("total high",g.total>g.total.quantile(2/3)),
             ("b2b diff!=0",g.b_b2b!=0),("b2b diff==0",g.b_b2b==0),("rest edge>=2",g.b_rest>=2)]:
    gg=g[m]; FC.append((nm,gg.win.values,gg.odds.values,gg.fair.values))
for s in sorted(g.season.unique()):
    gg=g[g.season==s]; FC.append((f"season {s}",gg.win.values,gg.odds.values,gg.fair.values))
bc=ceiling(FC,minn=40); p95c=np.percentile(bc,95)
print(f"  {len(FC)} cells. NOISE CEILING p95={p95c:+.2f}% (p50={np.percentile(bc,50):+.2f}%)")
for lb,w,od,fp in FC:
    if len(w)<20: continue
    roi=np.where(w,od-1,-1).mean()*100; lo,hi=bootci(w,od)
    fl=" <<< CLEARS" if roi>p95c and len(w)>=40 else ""
    print(f"  {lb:16} {len(w):5d} hit={w.mean()*100:6.2f}% ROI={roi:+7.2f}% [{lo:+6.2f},{hi:+6.2f}]{fl}")

# ---- MECHANISM: does edge predict ATS at all, in raw points? ----
print("\n--- MECHANISM: regression ats ~ edge (raw points, no betting) ---")
for nm,gg in SETS.items():
    x=gg.edge.values; y=gg.ats.values
    X=np.column_stack([np.ones(len(x)),x]); b=np.linalg.lstsq(X,y,rcond=None)[0]
    r=y-X@b; se=np.sqrt((r@r/(len(x)-2))*np.linalg.inv(X.T@X)[1,1])
    print(f"  {nm:28} beta={b[1]:+.4f} se={se:.4f} t={b[1]/se:+.2f}  n={len(x)}"
          f"   -> a 5pt edge is worth {5*b[1]:+.2f} real pts")
    # per-season betas (walk-forward stability)
    ln="      per-season beta:"
    for s in sorted(gg.season.unique()):
        h=gg[gg.season==s]; X2=np.column_stack([np.ones(len(h)),h.edge.values])
        b2=np.linalg.lstsq(X2,h.ats.values,rcond=None)[0]
        ln+=f" {s}:{b2[1]:+.2f}"
    print(ln)
