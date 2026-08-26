# FAMILY A: "line shape" - does the closing spread over/under-extend? Grid DECLARED BEFORE results.
# GRID (declared): side in {fav,dog,home,away} x bucket in {0.5-3.5,4-7.5,8-11.5,12+} = 16 cells
#   PLUS threshold sweep |spread|>=T for T in {6,8,10,12,14} x side in {fav,dog} = 10 cells
#   => 26 cells total. Null = market exactly calibrated (win prob = de-vigged fair prob, real odds).
import numpy as np, pandas as pd, os
D=r"C:\Users\Axioo\wnba-line-capture"
sp=pd.read_csv(os.path.join(D,"outputs","gm","gm_sp_work.csv"))
sp=sp[sp.ats!=0].copy()   # pushes (n=2) removed from ROI; reported separately
rng=np.random.default_rng(11)

def devig(oa,ob):
    ia,ib=1/oa,1/ob; s=ia+ib; return ia/s
sp["fair_fav"]=[devig(a,b) for a,b in zip(sp.fav_odds,sp.dog_odds)]
sp["fair_home"]=[devig(a,b) for a,b in zip(sp.sp_h,sp.sp_a)]

def cells(df):
    """returns list of (label, win_bool_array, odds_array, fairprob_array)"""
    out=[]
    bkts=[("0.5-3.5",0.5,3.5),("4-7.5",3.51,7.5),("8-11.5",7.51,11.5),("12+",11.51,99)]
    a=df.spread.abs().values
    for nm,lo,hi in bkts:
        m=(a>=lo)&(a<=hi)
        g=df[m]
        out.append((f"FAV {nm}", g.fav_cov.values==1, g.fav_odds.values, g.fair_fav.values))
        out.append((f"DOG {nm}", g.fav_cov.values==0, g.dog_odds.values, 1-g.fair_fav.values))
        out.append((f"HOME {nm}", g.cov_h.values==1, g.sp_h.values, g.fair_home.values))
        out.append((f"AWAY {nm}", g.cov_h.values==0, g.sp_a.values, 1-g.fair_home.values))
    for T in (6,8,10,12,14):
        g=df[a>=T]
        out.append((f"FAV |sp|>={T}", g.fav_cov.values==1, g.fav_odds.values, g.fair_fav.values))
        out.append((f"DOG |sp|>={T}", g.fav_cov.values==0, g.dog_odds.values, 1-g.fair_fav.values))
    return out

C=cells(sp)
print(f"GRID declared: {len(C)} cells, n range {min(len(c[1]) for c in C)}-{max(len(c[1]) for c in C)}")
# ---- NOISE CEILING (computed BEFORE printing real results) ----
B=4000
best=np.empty(B)
for b in range(B):
    mx=-9
    for lb,win,od,fp in C:
        if len(win)<50: continue
        w=rng.random(len(fp))<fp
        r=np.where(w,od-1,-1).mean()*100
        mx=max(mx,r)
    best[b]=mx
print(f"NOISE CEILING (market-calibrated null, cells n>=50): best-cell ROI p50={np.percentile(best,50):+.2f}%  p95={np.percentile(best,95):+.2f}%  p99={np.percentile(best,99):+.2f}%")
print("  -> any real cell below p95 is NOT a finding.\n")

def bootci(win,od,B=4000):
    n=len(win); pnl=np.where(win,od-1,-1)
    idx=rng.integers(0,n,(B,n))
    r=pnl[idx].mean(axis=1)*100
    return np.percentile(r,2.5),np.percentile(r,97.5)
print(f"{'cell':18} {'n':>5} {'hit%':>7} {'fair%':>7} {'ROI%':>8}  95% CI")
for lb,win,od,fp in C:
    if len(win)<20: continue
    roi=np.where(win,od-1,-1).mean()*100
    lo,hi=bootci(win,od)
    flag=" <<< CLEARS CEILING" if roi>np.percentile(best,95) and len(win)>=50 else ""
    print(f"{lb:18} {len(win):5d} {win.mean()*100:6.2f}% {fp.mean()*100:6.2f}% {roi:+7.2f}%  [{lo:+6.2f},{hi:+6.2f}]{flag}")

# ---- walk-forward check on the best-looking line-shape cell: big dogs ----
print("\n--- BIG DOG (|spread|>=12) by season ---")
g=sp[sp.spread.abs()>=12]
for s,gg in g.groupby("season"):
    win=gg.fav_cov.values==0; roi=np.where(win,gg.dog_odds.values-1,-1).mean()*100
    print(f"  {s} n={len(gg):3d} hit={win.mean()*100:5.1f}% ROI={roi:+6.2f}%")
print("\n--- FAV |spread|>=12 by season (mirror) ---")
for s,gg in g.groupby("season"):
    win=gg.fav_cov.values==1; roi=np.where(win,gg.fav_odds.values-1,-1).mean()*100
    print(f"  {s} n={len(gg):3d} hit={win.mean()*100:5.1f}% ROI={roi:+6.2f}%")

# ---- MECHANISM: slope test restricted, and mean ATS by line decile ----
print("\n--- mean ATS (from fav's view: fav_margin - fav_line) by |spread| decile ---")
sp["favmarg"]=np.where(sp.fav_is_home, sp.home_margin, -sp.home_margin)
sp["favline"]=sp.spread.abs()
sp["fav_ats"]=sp.favmarg-sp.favline
sp["dec"]=pd.qcut(sp.favline,10,duplicates="drop")
for lb,gg in sp.groupby("dec",observed=True):
    se=gg.fav_ats.std()/np.sqrt(len(gg))
    print(f"  line {str(lb):18} n={len(gg):4d} mean_favATS={gg.fav_ats.mean():+6.2f} (se {se:.2f}, t={gg.fav_ats.mean()/se:+5.2f}) favcover={100*(gg.fav_ats>0).mean():5.1f}%")
# regression favATS ~ favline
x=sp.favline.values; y=sp.fav_ats.values
X=np.column_stack([np.ones(len(x)),x]); bb=np.linalg.lstsq(X,y,rcond=None)[0]
res=y-X@bb; se_b=np.sqrt((res@res/(len(x)-2))*np.linalg.inv(X.T@X)[1,1])
print(f"\n  favATS = {bb[0]:+.3f} + {bb[1]:+.4f}*favline   se(slope)={se_b:.4f}  t={bb[1]/se_b:+.2f}")
print("  (negative slope = the market over-extends big favourites -> bet dogs)")
