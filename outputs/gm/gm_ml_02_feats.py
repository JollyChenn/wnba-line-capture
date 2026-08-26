# Build own all-season pre-game features (2019-2026) from games_full.csv
import pandas as pd, numpy as np, os
from collections import defaultdict, deque
from datetime import date
g=pd.read_csv("elo_model/games_full.csv")
g=g.dropna(subset=["home_score","away_score"]).sort_values(["date","game_id"]).reset_index(drop=True)
def pd_(s):
    s=str(int(s)); return date(int(s[:4]),int(s[4:6]),int(s[6:8]))
elo=defaultdict(lambda:1500.0)
last={}; form=defaultdict(lambda:deque(maxlen=5)); form10=defaultdict(lambda:deque(maxlen=10))
gp=defaultdict(int); season_cur=None
rows=[]
for r in g.itertuples():
    if r.season!=season_cur:
        for k in list(elo): elo[k]=1500+0.7*(elo[k]-1500)
        season_cur=r.season; last={}; gp=defaultdict(int)
    dt=pd_(r.date)
    def rest(t):
        return min((dt-last[t]).days,7) if t in last else 4
    rh,ra=rest(r.home),rest(r.away)
    f5h=np.mean(form[r.home]) if form[r.home] else 0.0
    f5a=np.mean(form[r.away]) if form[r.away] else 0.0
    f10h=np.mean(form10[r.home]) if form10[r.home] else 0.0
    f10a=np.mean(form10[r.away]) if form10[r.away] else 0.0
    rows.append(dict(game_id=r.game_id,season=r.season,
        o_elo=elo[r.home]-elo[r.away], o_rest=rh-ra,
        o_b2b=(1 if rh<=1 else 0)-(1 if ra<=1 else 0),
        o_b2bh=1 if rh<=1 else 0, o_b2ba=1 if ra<=1 else 0,
        o_form5=f5h-f5a, o_form10=f10h-f10a,
        o_gp=min(gp[r.home],gp[r.away]),
        o_eloh=elo[r.home], o_eloa=elo[r.away]))
    m=r.home_score-r.away_score
    eh=1/(1+10**(-(elo[r.home]+80-elo[r.away])/400))
    mov=np.log(abs(m)+1)*2.2/(0.001*abs(elo[r.home]+80-elo[r.away])+2.2)
    k=20*mov*((1 if m>0 else 0)-eh)
    elo[r.home]+=k; elo[r.away]-=k
    form[r.home].append(m); form[r.away].append(-m)
    form10[r.home].append(m); form10[r.away].append(-m)
    last[r.home]=dt; last[r.away]=dt; gp[r.home]+=1; gp[r.away]+=1
o=pd.DataFrame(rows)
o.to_csv("outputs/gm/gm_own_feats.csv",index=False)
print(o.shape, o.describe().T[["mean","std","min","max"]])
# sanity: elo predicts outcome
d=pd.read_csv("outputs/gm/gm_ml_base.csv").merge(o,on=["game_id","season"],how="left")
print("corr(o_elo, home_margin)=%.3f ; corr(o_elo, market -spread)=%.3f"%(
  d.o_elo.corr(d.home_margin), d.o_elo.corr(-d.spread)))
print("corr(o_elo, ATS resid)=%.3f  n=%d"%(d.o_elo.corr(d.home_margin+d.spread), d.o_elo.notna().sum()))
