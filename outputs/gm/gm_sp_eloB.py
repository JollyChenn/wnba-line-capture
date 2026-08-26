# MODEL B: wider sample. Walk-forward team Elo + rest/b2b/form/home built from games_full only,
# so it covers 2019-2026 (vs feats_v5's 2023-2026). Strictly pre-game: every game is predicted
# BEFORE its own result updates the ratings.
import numpy as np, pandas as pd, os
from collections import defaultdict, deque
from datetime import date
D=r"C:\Users\Axioo\wnba-line-capture"
df=pd.read_csv(os.path.join(D,"outputs","gm","gm_dataset.csv")).sort_values(["date","game_id"]).reset_index(drop=True)
def dt(s):
    s=str(int(s)); return date(int(s[:4]),int(s[4:6]),int(s[6:8]))
elo=defaultdict(lambda:1500.0); last={}; form=defaultdict(lambda:deque(maxlen=5)); gpl=defaultdict(int)
rows=[]; cur=None
K=20.0; HFA=80.0
for i,g in df.iterrows():
    if g.season!=cur:
        cur=g.season
        for k in list(elo): elo[k]=1500+0.7*(elo[k]-1500)
        last.clear()
    h,a=g.home,g.away; d=dt(g.date)
    rh=(min((d-last[h]).days,5) if h in last else 3); ra=(min((d-last[a]).days,5) if a in last else 3)
    fh=np.mean(form[h]) if form[h] else 0.0; fa=np.mean(form[a]) if form[a] else 0.0
    rows.append(dict(game_id=g.game_id, season=g.season, elo_d=elo[h]-elo[a]+HFA,
                     b_rest=rh-ra, b_b2b=(1 if rh<=1 else 0)-(1 if ra<=1 else 0),
                     b_form5=fh-fa, gp_min=min(gpl[h],gpl[a])))
    if pd.notna(g.home_margin):
        m=g.home_margin; ed=elo[h]+HFA-elo[a]; eh=1/(1+10**(-ed/400))
        mov=(abs(m)+3)**0.8/(7.5+0.006*abs(ed))
        elo[h]+=K*mov*((1 if m>0 else 0)-eh); elo[a]-=K*mov*((1 if m>0 else 0)-eh)
        form[h].append(m); form[a].append(-m); gpl[h]+=1; gpl[a]+=1
    last[h]=d; last[a]=d
E=pd.DataFrame(rows)
d=df.merge(E,on=["game_id","season"]).dropna(subset=["spread","sp_h","sp_a","home_margin"]).copy()
d=d[d.gp_min>=5]
d["mkt"]=-d.spread; d["ats"]=d.home_margin-d.mkt
print("Model B rows:",len(d)); print(d.groupby("season").size().to_string())
FB=["elo_d","b_rest","b_b2b","b_form5"]
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
preds=np.full(len(d),np.nan); idx=np.arange(len(d))
for s in sorted(d.season.unique()):
    tr=(d.season<s).values; te=(d.season==s).values
    if tr.sum()<200: continue
    sc=StandardScaler().fit(d.loc[tr,FB].values)
    m=Ridge(alpha=10).fit(sc.transform(d.loc[tr,FB].values), d.loc[tr,"home_margin"].values)
    preds[idx[te]]=m.predict(sc.transform(d.loc[te,FB].values))
d["predB"]=preds
ok=d.predB.notna()
print(f"\nModel B walk-forward, n={ok.sum()}")
print(f"{'season':8}{'n':>6}{'model RMSE':>12}{'mkt RMSE':>12}{'corr(edge,ats)':>16}")
for s in sorted(d.loc[ok,"season"].unique()):
    g=d[ok&(d.season==s)]
    rm=np.sqrt(((g.predB-g.home_margin)**2).mean()); rk=np.sqrt(((g.mkt-g.home_margin)**2).mean())
    e=g.predB-g.mkt
    print(f"{s:<8}{len(g):>6}{rm:>12.2f}{rk:>12.2f}{np.corrcoef(e,g.ats)[0,1]:>16.4f}")
g=d[ok]
rm=np.sqrt(((g.predB-g.home_margin)**2).mean()); rk=np.sqrt(((g.mkt-g.home_margin)**2).mean())
e=(g.predB-g.mkt).values; a=g.ats.values
print(f"{'ALL':<8}{len(g):>6}{rm:>12.2f}{rk:>12.2f}{np.corrcoef(e,a)[0,1]:>16.4f}  t={np.corrcoef(e,a)[0,1]*np.sqrt(len(g)-2):+.2f}")
print(f"  edge sd={e.std():.2f}, mean|edge|={np.abs(e).mean():.2f}")
d.to_csv(os.path.join(D,"outputs","gm","gm_modelB_rows.csv"),index=False)
