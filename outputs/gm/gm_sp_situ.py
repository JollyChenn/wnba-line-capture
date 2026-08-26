# FAMILY D: situational / behavioural spread angles on the FULL priced sample (n=1830).
# GRID DECLARED BEFORE RESULTS. 13 splits x 2 sides = 26 cells. All features strictly pre-game
# (built from games strictly EARLIER in the chronological pass).
import numpy as np, pandas as pd, os
from collections import defaultdict, deque
from datetime import date
D=r"C:\Users\Axioo\wnba-line-capture"
rng=np.random.default_rng(31)
df=pd.read_csv(os.path.join(D,"outputs","gm","gm_dataset.csv")).sort_values(["date","game_id"]).reset_index(drop=True)
def dt(s):
    s=str(int(s)); return date(int(s[:4]),int(s[4:6]),int(s[6:8]))
last={}; lastmarg=defaultdict(lambda:None); streak=defaultdict(int); roadrun=defaultdict(int)
h2h={}; gcount=defaultdict(int); rows=[]; cur=None
for i,g in df.iterrows():
    if g.season!=cur:
        cur=g.season; last.clear(); streak.clear(); roadrun.clear(); h2h.clear(); gcount.clear()
        lastmarg.clear()
    h,a=g.home,g.away; d=dt(g.date)
    rh=(min((d-last[h]).days,7) if h in last else 3); ra=(min((d-last[a]).days,7) if a in last else 3)
    key=tuple(sorted([h,a])); prev=h2h.get(key)
    rows.append(dict(game_id=g.game_id, rest_h=rh, rest_a=ra,
        b2b_h=int(rh<=1), b2b_a=int(ra<=1),
        lm_h=lastmarg[h], lm_a=lastmarg[a], stk_h=streak[h], stk_a=streak[a],
        roadrun_a=roadrun[a], gnum=min(gcount[h],gcount[a]),
        rematch_days=(d-prev[0]).days if prev else None,
        prev_win_home=(1 if prev and prev[1]==h else 0) if prev else None))
    if pd.notna(g.home_margin):
        m=g.home_margin
        lastmarg[h]=m; lastmarg[a]=-m
        streak[h]=streak[h]+1 if m>0 else (min(streak[h],0)-1 if m<0 else 0)
        streak[a]=streak[a]+1 if m<0 else (min(streak[a],0)-1 if m>0 else 0)
        h2h[key]=(d, h if m>0 else a)
        gcount[h]+=1; gcount[a]+=1
    roadrun[a]+=1; roadrun[h]=0
    last[h]=d; last[a]=d
S=pd.DataFrame(rows)
d=df.merge(S,on="game_id").dropna(subset=["spread","sp_h","sp_a","home_margin"]).copy()
d["mkt"]=-d.spread; d["ats"]=d.home_margin-d.mkt
d=d[d.ats!=0]
ih,ia=1/d.sp_h,1/d.sp_a; d["fair_h"]=ih/(ih+ia)
print("Family D sample:",len(d))

SPLITS=[
 ("home on b2b, away rested", (d.b2b_h==1)&(d.b2b_a==0)),
 ("away on b2b, home rested", (d.b2b_a==1)&(d.b2b_h==0)),
 ("home rest>=3 vs away<=1",  (d.rest_h>=3)&(d.rest_a<=1)),
 ("home off 20+ pt LOSS",     (d.lm_h<=-20)),
 ("home off 20+ pt WIN",      (d.lm_h>=20)),
 ("away off 20+ pt LOSS",     (d.lm_a<=-20)),
 ("away off 20+ pt WIN",      (d.lm_a>=20)),
 ("home win streak>=3",       (d.stk_h>=3)),
 ("away win streak>=3",       (d.stk_a>=3)),
 ("home DOG (sp>0)",          (d.spread>0)),
 ("away 3rd+ straight road",  (d.roadrun_a>=3)),
 ("rematch within 14d",       (d.rematch_days<=14)),
 ("late season (gnum>=25)",   (d.gnum>=25)),
]
def mk(lbl,mask,bet_home):
    g=d[mask]
    od=(g.sp_h if bet_home else g.sp_a).values
    win=((g.ats>0) if bet_home else (g.ats<0)).values
    fp=(g.fair_h if bet_home else 1-g.fair_h).values
    return (f"{lbl} -> {'HOME' if bet_home else 'AWAY'}", win, od, fp)
C=[mk(l,m,b) for l,m in SPLITS for b in (True,False)]
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
bst=ceiling(C); p95=np.percentile(bst,95)
print(f"\n{len(C)} cells declared. NOISE CEILING (cells n>=40): p50={np.percentile(bst,50):+.2f}% p95={p95:+.2f}% p99={np.percentile(bst,99):+.2f}%\n")
def bootci(w,od,B_=4000):
    n=len(w); pnl=np.where(w,od-1,-1); i=rng.integers(0,n,(B_,n)); r=pnl[i].mean(axis=1)*100
    return np.percentile(r,2.5),np.percentile(r,97.5)
print(f"{'cell':40} {'n':>5} {'hit%':>7} {'ROI%':>8}  95% CI")
best_cells=[]
for lb,w,od,fp in C:
    if len(w)<25: continue
    roi=np.where(w,od-1,-1).mean()*100; lo,hi=bootci(w,od)
    fl=" <<< CLEARS" if roi>p95 and len(w)>=40 else ""
    print(f"{lb:40} {len(w):5d} {w.mean()*100:6.2f}% {roi:+7.2f}%  [{lo:+6.2f},{hi:+6.2f}]{fl}")
    best_cells.append((roi,lb,len(w)))
best_cells.sort(reverse=True)
print("\nTOP 3 by ROI:", [(f"{r:+.2f}%",l,n) for r,l,n in best_cells[:3]])
print(f"CEILING p95 = {p95:+.2f}%  -> clears: {sum(1 for r,l,n in best_cells if r>p95 and n>=40)}")

# ---- MECHANISM on raw points for the strongest split, both directions ----
print("\n--- raw-points mechanism (mean ATS from the named side's view) ---")
for lbl,mask in SPLITS:
    g=d[mask]
    if len(g)<25: continue
    se=g.ats.std()/np.sqrt(len(g))
    print(f"  {lbl:28} n={len(g):4d} mean home-ATS={g.ats.mean():+6.2f} (se {se:.2f}, t={g.ats.mean()/se:+5.2f})")
d.to_csv(os.path.join(D,"outputs","gm","gm_situ_rows.csv"),index=False)
