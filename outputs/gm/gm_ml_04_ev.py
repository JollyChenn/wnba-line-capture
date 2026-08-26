import pandas as pd, numpy as np, warnings
warnings.filterwarnings("ignore")
rng=np.random.default_rng(7)
p=pd.read_csv("outputs/gm/gm_preds.csv")
MODELS=["M2own_mkt+elo+rest+b2b","M3own_+form","M4own_ridge","M5own_gbm","NoMkt_own",
        "M2_mkt+telo+rest+b2b+road","M3_+form_pace_eff","M4_ridge_all30","M5_gbm_all30","NoMkt_all30"]
THR=[0.0,0.01,0.02,0.03,0.05]
SIDES=["both","home","away"]
NCELL=len([m for m in MODELS])*len(THR)*len(SIDES)
print("DECLARED GRID (EV stage): %d models x %d thresholds x %d side-restrictions = %d cells"%(len(MODELS),len(THR),len(SIDES),NCELL))
print("NULL: market close is the true probability. Resample home_won ~ Bernoulli(p_mkt_devig) per game,")
print("      keep all model predictions and real prices fixed, recompute every cell, take max ROI over cells with n>=40.")

def cells(y, ph_all, mask_all):
    out=[]
    for m in MODELS:
        pm=p[m].values
        ok=mask_all & ~np.isnan(pm)
        evh=pm*p.ml_h.values-1; eva=(1-pm)*p.ml_a.values-1
        for t in THR:
            for s in SIDES:
                bh=(evh>t)&ok; ba=(eva>t)&ok
                if s=="both":
                    pick_h=bh&(evh>=eva); pick_a=ba&(eva>evh)
                elif s=="home": pick_h=bh; pick_a=np.zeros(len(p),bool)
                else: pick_h=np.zeros(len(p),bool); pick_a=ba
                n=pick_h.sum()+pick_a.sum()
                if n<40: out.append((m,t,s,n,np.nan)); continue
                pnl=np.concatenate([y[pick_h]*(p.ml_h.values[pick_h]-1)-(1-y[pick_h]),
                                    (1-y[pick_a])*(p.ml_a.values[pick_a]-1)-y[pick_a]])
                out.append((m,t,s,n,pnl.mean()*100))
    return out

mask=p[MODELS].notna().any(axis=1).values & p.p_mkt.notna().values
# ---- NOISE CEILING FIRST ----
best=[]
pmkt=p.p_mkt.values
for it in range(2000):
    ysim=(rng.random(len(p))<pmkt).astype(float)
    r=[c[4] for c in cells(ysim,None,mask) if not np.isnan(c[4])]
    best.append(max(r))
best=np.array(best)
print("\nNOISE CEILING: best-of-%d-cell ROI under the null  p50=%.2f%%  p95=%.2f%%  p99=%.2f%%"%(NCELL,np.percentile(best,50),np.percentile(best,95),np.percentile(best,99)))
CEIL=np.percentile(best,95)

y=p.y.values
res=cells(y,None,mask)
print("\n=== REAL EV-THRESHOLD CURVE (bold = above ceiling) ===")
print(f"{'model':>28} {'thr':>5} {'side':>5} {'n':>5} {'ROI%':>8}  flag")
for m,t,s,n,roi in res:
    if np.isnan(roi): continue
    if s!="both" and t not in (0.0,0.03): continue
    print(f"{m:>28} {t:>5.2f} {s:>5} {n:>5} {roi:>+8.2f}  {'*ABOVE CEIL*' if roi>CEIL else ''}")
mx=max([c for c in res if not np.isnan(c[4])],key=lambda c:c[4])
print("\nBest real cell: %s thr=%.2f side=%s n=%d ROI=%+.2f%%  (ceiling %.2f%%)"%(mx[0],mx[1],mx[2],mx[3],mx[4],CEIL))
print("VERDICT EV STAGE:", "ABOVE CEILING" if mx[4]>CEIL else "BELOW NOISE CEILING - not a finding")
