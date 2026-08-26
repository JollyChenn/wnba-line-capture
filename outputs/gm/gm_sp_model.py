# STEP 2: model the home margin, walk-forward by season. Compare RMSE to the closing line's own RMSE.
import numpy as np, pandas as pd, os
from sklearn.linear_model import Ridge, ElasticNet
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
D=r"C:\Users\Axioo\wnba-line-capture"
df=pd.read_csv(os.path.join(D,"outputs","gm","gm_dataset.csv"))
FE=["pstr","pnews","telo","zone","rest","b2b","form5","pace_d","pace_s","tov","oreb","ftr","p3ar",
    "p3pct","stk","bench","drop","fluid","pmr","pfr","ftp","blkr","q4","road","m_scdef","m_pade",
    "m_rb","m_vo","m_all5","lgenv"]
d=df.dropna(subset=FE+["spread","sp_h","sp_a","home_margin"]).copy()
d["mkt"]=-d.spread; d["ats"]=d.home_margin-d.mkt
print("modelling rows:",len(d)); print(d.groupby("season").size().to_string())

def wf(model_fn, target, use_mkt):
    """expanding window: train on seasons < s, predict s. target: 'margin' or 'ats'."""
    preds=np.full(len(d),np.nan); idx=np.arange(len(d))
    for s in sorted(d.season.unique()):
        tr=d.season<s; te=d.season==s
        if tr.sum()<200: continue
        cols=FE+(["mkt"] if use_mkt else [])
        Xtr=d.loc[tr,cols].values; Xte=d.loc[te,cols].values
        sc=StandardScaler().fit(Xtr)
        ytr=d.loc[tr,"home_margin"].values if target=="margin" else d.loc[tr,"ats"].values
        m=model_fn(); m.fit(sc.transform(Xtr),ytr)
        p=m.predict(sc.transform(Xte))
        preds[idx[te]]= p if target=="margin" else d.loc[te,"mkt"].values+p
    return preds

MODELS={
 "ridge a=30":       lambda: Ridge(alpha=30),
 "ridge a=100":      lambda: Ridge(alpha=100),
 "ridge a=300":      lambda: Ridge(alpha=300),
 "enet a=1 l1=.5":   lambda: ElasticNet(alpha=1.0,l1_ratio=0.5,max_iter=5000),
 "gbm d3 lr.05":     lambda: HistGradientBoostingRegressor(max_depth=3,learning_rate=0.05,max_iter=300,min_samples_leaf=30,random_state=0),
}
res={}
print(f"\n{'model':28} {'target':8} {'mkt?':5} " + " ".join(f"{s:>17}" for s in [2024,2025,2026]) + "   ALL")
for target in ("margin","ats"):
  for use_mkt in (False,True):
    if target=="ats" and use_mkt: continue
    for nm,fn in MODELS.items():
        p=wf(fn,target,use_mkt)
        row=[]
        ok=~np.isnan(p)
        for s in [2024,2025,2026]:
            m=(d.season.values==s)&ok
            if m.sum()==0: row.append("       -        "); continue
            rm=np.sqrt(((p[m]-d.home_margin.values[m])**2).mean())
            rk=np.sqrt(((d.mkt.values[m]-d.home_margin.values[m])**2).mean())
            row.append(f"{rm:6.2f} vs {rk:6.2f}")
        m=ok
        rm=np.sqrt(((p[m]-d.home_margin.values[m])**2).mean()); rk=np.sqrt(((d.mkt.values[m]-d.home_margin.values[m])**2).mean())
        print(f"{nm:28} {target:8} {str(use_mkt):5} " + " ".join(f"{x:>17}" for x in row) + f"   {rm:6.2f} vs {rk:6.2f}  n={m.sum()}")
        res[(nm,target,use_mkt)]=p
np.save(os.path.join(D,"outputs","gm","gm_preds.npy"),
        np.array([res[k] for k in sorted(res,key=str)]))
import pickle
pickle.dump({str(k):v for k,v in res.items()}, open(os.path.join(D,"outputs","gm","gm_preds.pkl"),"wb"))
d.to_csv(os.path.join(D,"outputs","gm","gm_model_rows.csv"),index=False)
# blend: does adding the model to the market help at all? OOS R2 of model on ATS residual
print("\nOOS R2 on the ATS residual (0 = market unbeatable):")
for k,p in res.items():
    ok=~np.isnan(p); e=p[ok]-d.mkt.values[ok]; a=d.ats.values[ok]
    r2=1-((a-e)**2).mean()/((a-a.mean())**2).mean()
    print(f"  {str(k):50} corr(edge,ats)={np.corrcoef(e,a)[0,1]:+.4f}  R2={r2:+.4f}")
