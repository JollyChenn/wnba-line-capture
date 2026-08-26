import pandas as pd, numpy as np, json, warnings
warnings.filterwarnings("ignore")
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
rng=np.random.default_rng(20260826)
d=pd.read_csv("outputs/gm/gm_ml_base.csv").merge(pd.read_csv("outputs/gm/gm_own_feats.csv"),on=["game_id","season"],how="left")
d["mlogit"]=np.log(d.p_mkt/(1-d.p_mkt))
FEAT30=["pstr","pnews","telo","zone","rest","b2b","form5","pace_d","pace_s","tov","oreb","ftr","p3ar","p3pct","stk","bench","drop","fluid","pmr","pfr","ftp","blkr","q4","road","m_scdef","m_pade","m_rb","m_vo","m_all5","lgenv"]
OWN=["o_elo","o_rest","o_b2b","o_form5","o_form10","o_gp"]
y=d.home_won.values

def metrics(p,yy):
    p=np.clip(p,1e-6,1-1e-6)
    return np.mean((p-yy)**2), -np.mean(yy*np.log(p)+(1-yy)*np.log(1-p))

def fit_predict(tr,te,cols,kind,C=1.0):
    Xtr=d.loc[tr,cols].values; Xte=d.loc[te,cols].values
    sc=StandardScaler().fit(Xtr); Xtr=sc.transform(Xtr); Xte=sc.transform(Xte)
    if kind=="lr":
        m=LogisticRegression(C=C,max_iter=2000).fit(Xtr,y[tr])
        return m.predict_proba(Xte)[:,1]
    m=HistGradientBoostingClassifier(max_iter=250,learning_rate=0.04,max_depth=3,
        min_samples_leaf=40,l2_regularization=1.0,random_state=0).fit(Xtr,y[tr])
    return m.predict_proba(Xte)[:,1]

def run(tag, mask, models, folds):
    print("\n"+"="*90); print("WALK-FORWARD:",tag)
    out={}
    for name,(cols,kind,C) in models.items():
        preds=np.full(len(d),np.nan)
        print(f"  -- {name} ({len(cols)} cols)")
        for T in folds:
            tr=np.where(mask & (d.season<T))[0]; te=np.where(mask & (d.season==T))[0]
            if len(tr)<120 or len(te)<20: continue
            p=fit_predict(tr,te,cols,kind,C); preds[te]=p
            b,l=metrics(p,y[te]); b0,l0=metrics(d.p_mkt.values[te],y[te])
            print(f"     {T} ntr={len(tr):4d} nte={len(te):3d} Brier {b:.5f} (M1 {b0:.5f}, d {b-b0:+.5f})  LL {l:.5f} (M1 {l0:.5f}, d {l-l0:+.5f})")
        m=~np.isnan(preds)
        b,l=metrics(preds[m],y[m]); b0,l0=metrics(d.p_mkt.values[m],y[m])
        print(f"     POOLED n={m.sum()} Brier {b:.5f} vs M1 {b0:.5f} ({b-b0:+.5f}) | LL {l:.5f} vs {l0:.5f} ({l-l0:+.5f})")
        out[name]=preds
    return out

feat_mask=d[FEAT30].notna().all(axis=1).values & d.p_mkt.notna().values
own_mask=d[OWN].notna().all(axis=1).values & d.p_mkt.notna().values
print("feat_mask n=%d (seasons %s)"%(feat_mask.sum(),sorted(d.season[feat_mask].unique())))
print("own_mask  n=%d"%own_mask.sum())

# ---- A: own features, all seasons, 6 folds
A=run("OWN FEATURES 2019-2026 (market + elo/rest/b2b/form)", own_mask, {
  "M2own_mkt+elo+rest+b2b":(["mlogit","o_elo","o_rest","o_b2b"],"lr",1.0),
  "M3own_+form":(["mlogit"]+OWN,"lr",1.0),
  "M4own_ridge":(["mlogit"]+OWN+["o_eloh","o_eloa","o_b2bh","o_b2ba"],"lr",0.1),
  "M5own_gbm":(["mlogit"]+OWN,"gbm",0),
  "NoMkt_own":(OWN,"lr",1.0),
}, [2021,2022,2023,2024,2025,2026])

# ---- B: feats_v5, 2023-2026
B=run("FEATS_V5 2023-2026", feat_mask, {
  "M2_mkt+telo+rest+b2b+road":(["mlogit","telo","rest","b2b","road"],"lr",1.0),
  "M3_+form_pace_eff":(["mlogit","telo","rest","b2b","road","form5","pace_d","pace_s","tov","oreb","ftr","p3ar","p3pct"],"lr",1.0),
  "M4_ridge_all30":(["mlogit"]+FEAT30,"lr",0.05),
  "M5_gbm_all30":(["mlogit"]+FEAT30,"gbm",0),
  "NoMkt_all30":(FEAT30,"lr",0.05),
}, [2024,2025,2026])

np.save("outputs/gm/gm_preds_A.npy",np.array([A[k] for k in A])); 
pd.DataFrame({**{k:v for k,v in A.items()},**{k:v for k,v in B.items()}}).assign(
    game_id=d.game_id,season=d.season,p_mkt=d.p_mkt,ml_h=d.ml_h,ml_a=d.ml_a,y=y,
    o_elo=d.o_elo,o_b2bh=d.o_b2bh,o_b2ba=d.o_b2ba,o_rest=d.o_rest,spread=d.spread
).to_csv("outputs/gm/gm_preds.csv",index=False)
print("\nwrote outputs/gm/gm_preds.csv")
