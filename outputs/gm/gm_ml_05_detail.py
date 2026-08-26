import pandas as pd, numpy as np, warnings
warnings.filterwarnings("ignore")
rng=np.random.default_rng(11)
p=pd.read_csv("outputs/gm/gm_preds.csv")
MODELS=["M2own_mkt+elo+rest+b2b","M3own_+form","M4own_ridge","M5own_gbm","NoMkt_own",
        "M2_mkt+telo+rest+b2b+road","M3_+form_pace_eff","M4_ridge_all30","M5_gbm_all30","NoMkt_all30"]
THR=[0.0,0.01,0.02,0.03,0.05]; SIDES=["both","home","away"]
def cells(y,minn):
    out=[]
    for m in MODELS:
        pm=p[m].values; ok=~np.isnan(pm)
        evh=pm*p.ml_h.values-1; eva=(1-pm)*p.ml_a.values-1
        for t in THR:
            for s in SIDES:
                bh=(evh>t)&ok; ba=(eva>t)&ok
                if s=="both": ph=bh&(evh>=eva); pa=ba&(eva>evh)
                elif s=="home": ph=bh; pa=np.zeros(len(p),bool)
                else: ph=np.zeros(len(p),bool); pa=ba
                n=ph.sum()+pa.sum()
                if n<minn: continue
                pnl=np.concatenate([y[ph]*(p.ml_h.values[ph]-1)-(1-y[ph]),(1-y[pa])*(p.ml_a.values[pa]-1)-y[pa]])
                out.append((m,t,s,n,pnl.mean()*100,ph,pa))
    return out
pm=p.p_mkt.values
for MIN in (150,250):
    b=[]
    for it in range(1500):
        ys=(rng.random(len(p))<pm).astype(float)
        b.append(max(c[4] for c in cells(ys,MIN)))
    b=np.array(b)
    print("SECONDARY CEILING (post-hoc n>=%d restriction): p50=%.2f p95=%.2f p99=%.2f  [%d cells survive]"%(
        MIN,np.percentile(b,50),np.percentile(b,95),np.percentile(b,99),len(cells(p.y.values,MIN))))
y=p.y.values
real=sorted(cells(y,250),key=lambda c:-c[4])[:5]
print("\nTop-5 real cells with n>=250:")
def boot(ph,pa,B=4000):
    idx=np.where(ph|pa)[0]
    pnl=np.where(ph[idx], y[idx]*(p.ml_h.values[idx]-1)-(1-y[idx]), (1-y[idx])*(p.ml_a.values[idx]-1)-y[idx])
    s=rng.integers(0,len(pnl),(B,len(pnl)))
    m=pnl[s].mean(1)*100
    return np.percentile(m,2.5),np.percentile(m,97.5)
for m,t,s,n,roi,ph,pa in real:
    lo,hi=boot(ph,pa)
    seas=[]
    for S in sorted(p.season.unique()):
        msk=(p.season.values==S)&(ph|pa)
        if msk.sum()<10: continue
        pnl=np.where(ph[msk],y[msk]*(p.ml_h.values[msk]-1)-(1-y[msk]),(1-y[msk])*(p.ml_a.values[msk]-1)-y[msk])
        seas.append(f"{S}:{pnl.mean()*100:+.1f}(n{msk.sum()})")
    print(f"  {m} thr{t} {s} n={n} ROI={roi:+.2f}% CI[{lo:+.2f},{hi:+.2f}]  {' '.join(seas)}")
