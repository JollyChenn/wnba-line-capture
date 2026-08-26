# STEP 1: is the closing spread an unbiased estimate of the home margin?
import numpy as np, pandas as pd, os, json
D=r"C:\Users\Axioo\wnba-line-capture"
df=pd.read_csv(os.path.join(D,"outputs","gm","gm_dataset.csv"))
print("rows", len(df))
sp=df.dropna(subset=["spread","sp_h","sp_a","home_margin"]).copy()
sp["mkt_margin"]=-sp["spread"]          # market's expected home margin
sp["ats"]=sp["home_margin"]-sp["mkt_margin"]
print("priced spread rows:", len(sp), "seasons:", sorted(sp.season.unique()))
# ---- pushes ----
push=(sp["ats"]==0)
print(f"PUSH rate: {push.mean()*100:.2f}%  (n_push={push.sum()} of {len(sp)})")
print("integer-line share:", (sp.spread%1==0).mean().round(4))

rng=np.random.default_rng(7)
def boot_ols(x,y,B=4000):
    n=len(x); out=np.empty((B,2))
    X=np.column_stack([np.ones(n),x])
    for b in range(B):
        i=rng.integers(0,n,n)
        try: out[b]=np.linalg.lstsq(X[i],y[i],rcond=None)[0]
        except Exception: out[b]=np.nan
    return out
x=sp["mkt_margin"].values; y=sp["home_margin"].values
X=np.column_stack([np.ones(len(x)),x])
b=np.linalg.lstsq(X,y,rcond=None)[0]
bs=boot_ols(x,y)
lo=np.nanpercentile(bs,2.5,axis=0); hi=np.nanpercentile(bs,97.5,axis=0)
print(f"\n=== CALIBRATION  margin = a + b*mkt_margin  (n={len(x)}) ===")
print(f"  intercept a = {b[0]:+.3f}  95% CI [{lo[0]:+.3f}, {hi[0]:+.3f}]   (H0: 0)")
print(f"  slope     b = {b[1]:+.4f}  95% CI [{lo[1]:+.4f}, {hi[1]:+.4f}]   (H0: 1)")
resid=y-X@b
print(f"  resid sd = {resid.std(ddof=2):.2f}   R2={1-resid.var()/y.var():.4f}")
print(f"  market RMSE (line as forecast) = {np.sqrt(((y-x)**2).mean()):.3f}")
print(f"  mean ATS residual = {sp['ats'].mean():+.3f}  (sd {sp['ats'].std():.2f}, se {sp['ats'].std()/np.sqrt(len(sp)):.3f})")

# per-season calibration
print("\n--- per season ---")
for s,g in sp.groupby("season"):
    xx=g.mkt_margin.values; yy=g.home_margin.values
    XX=np.column_stack([np.ones(len(xx)),xx]); bb=np.linalg.lstsq(XX,yy,rcond=None)[0]
    print(f"  {s} n={len(g):4d} a={bb[0]:+6.2f} b={bb[1]:+6.3f} meanATS={g.ats.mean():+6.2f} homecover={(g.ats>0).mean()*100:5.1f}%")

# ---- cover rate & ROI by spread bucket (home side), plus de-vig fair prob ----
def devig(oa,ob):
    ia,ib=1/oa,1/ob; s=ia+ib; return ia/s, ib/s
sp["fair_h"],sp["fair_a"]=zip(*[devig(a,b) for a,b in zip(sp.sp_h,sp.sp_a)])
sp["cov_h"]=np.where(sp.ats>0,1,np.where(sp.ats<0,0,np.nan))
print("\n--- home-cover vs de-vigged fair prob, by |spread| bucket ---")
bins=[-0.01,0.5,3.5,7.5,11.5,100]; labs=["pk(0)","small 0.5-3.5","med 4-7.5","large 8-11.5","huge 12+"]
sp["bkt"]=pd.cut(sp.spread.abs(),bins=bins,labels=labs)
for lb,g in sp.groupby("bkt",observed=True):
    gg=g.dropna(subset=["cov_h"])
    roi_h=np.where(gg.cov_h==1,gg.sp_h-1,-1).mean()*100
    roi_a=np.where(gg.cov_h==0,gg.sp_a-1,-1).mean()*100
    print(f"  {lb:16} n={len(g):4d} push={100*(g.ats==0).mean():4.1f}%  homecover={gg.cov_h.mean()*100:5.2f}% fair_h={gg.fair_h.mean()*100:5.2f}%  ROI_home={roi_h:+6.2f} ROI_away={roi_a:+6.2f}  meanATS={g.ats.mean():+5.2f}")

print("\n--- FAV/DOG cover by |spread| bucket (fav side) ---")
sp["fav_is_home"]=sp.spread<0
sp["fav_cov"]=np.where(sp.fav_is_home, sp.cov_h, 1-sp.cov_h)
sp["fav_odds"]=np.where(sp.fav_is_home, sp.sp_h, sp.sp_a)
sp["dog_odds"]=np.where(sp.fav_is_home, sp.sp_a, sp.sp_h)
for lb,g in sp.groupby("bkt",observed=True):
    gg=g.dropna(subset=["fav_cov"])
    if len(gg)<5: continue
    roi_f=np.where(gg.fav_cov==1,gg.fav_odds-1,-1).mean()*100
    roi_d=np.where(gg.fav_cov==0,gg.dog_odds-1,-1).mean()*100
    print(f"  {lb:16} n={len(gg):4d} favcover={gg.fav_cov.mean()*100:5.2f}%  ROI_fav={roi_f:+6.2f} ROI_dog={roi_d:+6.2f}")

# ---- mechanism 6: realised margin dist conditional on line ----
print("\n--- realised home margin distribution vs closing line ---")
for lb,g in sp.groupby("bkt",observed=True):
    print(f"  {lb:16} n={len(g):4d} mean_line={g.mkt_margin.mean():+6.2f} mean_margin={g.home_margin.mean():+6.2f} sd_margin={g.home_margin.std():5.2f} sd_ats={g.ats.std():5.2f} skewATS={g.ats.skew():+.2f}")
# ats sd as function of |spread| -> does variance grow with line (blowout dynamics)?
print("\n  corr(|spread|, |ats|) =", round(np.corrcoef(sp.spread.abs(),sp.ats.abs())[0,1],4))
print("  corr(|spread|, ats)  =", round(np.corrcoef(sp.spread.abs(),sp.ats)[0,1],4))
sp.to_csv(os.path.join(D,"outputs","gm","gm_sp_work.csv"),index=False)
