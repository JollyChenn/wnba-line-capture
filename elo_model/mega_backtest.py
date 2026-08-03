# mega_backtest.py - THE DECISIVE TEST: model vs real multi-book closings 2019-2026 (be_odds.csv).
# Expanding-window: predict each season using coefficients fit ONLY on prior seasons (2019-20 warmup).
# Tests: ATS all/filtered/dog-side/big-spread-dog; ML dogs; totals both sides. z vs proper breakevens.
import csv,math,statistics,sys
try:sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception:pass
def f(x):
    try:return float(x)
    except:return None
NICK={"atlanta-dream":"ATL","chicago-sky":"CHI","connecticut-sun":"CON","dallas-wings":"DAL","indiana-fever":"IND",
"las-vegas-aces":"LV","los-angeles-sparks":"LA","minnesota-lynx":"MIN","new-york-liberty":"NY","phoenix-mercury":"PHX",
"seattle-storm":"SEA","washington-mystics":"WSH","golden-state-valkyries":"GS","portland-fire":"POR","toronto-tempo":"TOR"}
def teams_of(slug):
    s=slug;out=[]
    for k in sorted(NICK,key=len,reverse=True):
        if k in s:out.append((s.index(k),NICK[k]));s=s.replace(k,"#"*len(k),1)
    out.sort();return [t for _,t in out] if len(out)==2 else None
be={}
for r in csv.DictReader(open('be_odds.csv',encoding='utf-8')):
    t=teams_of(r['slug'])
    if not t:continue
    be[(r['season'],t[0],t[1],r['hscore'],r['ascore'])]=r
rows=list(csv.DictReader(open('feats_v3.csv',encoding='utf-8')))
games={g['game_id']:g for g in csv.DictReader(open('games_full.csv',encoding='utf-8'))}
V=['pnews','telo','oreb','p3ar']
def ols(X,y):
    k=len(X[0])
    XtX=[[sum(X[i][p]*X[i][q] for i in range(len(X)))+(1e-3 if p==q else 0) for q in range(k)] for p in range(k)]
    Xty=[sum(X[i][p]*y[i] for i in range(len(X))) for p in range(k)]
    M=[row[:]+[Xty[i]] for i,row in enumerate(XtX)]
    for c in range(k):
        pv=max(range(c,k),key=lambda r_:abs(M[r_][c]));M[c],M[pv]=M[pv],M[c]
        if abs(M[c][c])<1e-12:return None
        M[c]=[v/M[c][c] for v in M[c]]
        for r_ in range(k):
            if r_!=c and M[r_][c]:M[r_]=[x2-M[r_][c]*y2 for x2,y2 in zip(M[r_],M[c])]
    return [M[i][k] for i in range(k)]
# expanding-window predictions
preds={}
seasons=sorted({r['season'] for r in rows})
for i,ssn in enumerate(seasons):
    prior=[r for r in rows if r['season']<ssn]
    if len(prior)<300:continue
    B=ols([[f(r[k]) or 0 for k in V]+[1] for r in prior],[f(r['margin']) or 0 for r in prior])
    for r in rows:
        if r['season']==ssn:
            preds[r['game_id']]=sum(b*(f(r[k]) or 0) for b,k in zip(B,V))+B[-1]
# join
J=[]
for r in rows:
    gid=r['game_id']
    if gid not in preds:continue
    g=games[gid]
    key=(g['season'],g['home'],g['away'],str(int(f(g['home_score']) or 0)),str(int(f(g['away_score']) or 0)))
    b=be.get(key)
    if not b:continue
    J.append((r,g,b,preds[gid]))
print(f"JOINED: {len(J)} games with model pred + real closings ({seasons[2]}-2026)")
def rep(lbl,w,l,pnl=None,be_=0.524):
    n=w+l
    if not n:return
    z=(w/n-be_)/math.sqrt(.25/n)
    s=f"{lbl:34} {w}-{l} ({100*w/n:.1f}%) z={z:+.1f}"
    if pnl is not None:s+=f"  P&L {pnl:+.1f}u"
    print(s)
# ATS tests (spread = home line sp; take home if pred+sp>0)
for th,lbl in ((0,"ATS all"),(2,"ATS |edge|>=2"),(3,"ATS |edge|>=3")):
    w=l=0;pnl=0
    for r,g,b,m in J:
        sp=f(b['spread']);marg=(f(g['home_score']) or 0)-(f(g['away_score']) or 0)
        if sp is None:continue
        e=m+sp
        if abs(e)<th or marg+sp==0:continue
        home=e>0
        o=f(b['sp_h']) if home else f(b['sp_a'])
        win=(marg+sp>0)==home
        w+=win;l+=not win;pnl+=((o or 1.9)-1) if win else -1
    rep(lbl,w,l,pnl)
# dog-side splits
for th in (2,):
    for want_dog,lbl in ((True,"ATS e>=2 DOG side only"),(False,"ATS e>=2 FAV side only")):
        w=l=0;pnl=0
        for r,g,b,m in J:
            sp=f(b['spread']);marg=(f(g['home_score']) or 0)-(f(g['away_score']) or 0)
            if sp is None:continue
            e=m+sp
            if abs(e)<th or marg+sp==0:continue
            home=e>0
            isdog=(sp>0)==home
            if isdog!=want_dog:continue
            o=f(b['sp_h']) if home else f(b['sp_a'])
            win=(marg+sp>0)==home
            w+=win;l+=not win;pnl+=((o or 1.9)-1) if win else -1
        rep(lbl,w,l,pnl)
w=l=0;pnl=0
for r,g,b,m in J:
    sp=f(b['spread']);marg=(f(g['home_score']) or 0)-(f(g['away_score']) or 0)
    if sp is None or abs(sp)<=8:continue
    e=m+sp
    if abs(e)<2 or marg+sp==0:continue
    home=e>0
    if ((sp>0)==home)!=True:continue
    o=f(b['sp_h']) if home else f(b['sp_a'])
    win=(marg+sp>0)==home
    w+=win;l+=not win;pnl+=((o or 1.9)-1) if win else -1
rep("DOGS vs BIG spreads(>8) e>=2",w,l,pnl)
# ML dogs
w=l=0;pnl=0
for r,g,b,m in J:
    oh,oa=f(b['ml_h']),f(b['ml_a']);marg=(f(g['home_score']) or 0)-(f(g['away_score']) or 0)
    if not oh or not oa:continue
    dog_home=oh>oa
    if (m>0)!=dog_home:continue
    o=oh if dog_home else oa
    win=(marg>0)==dog_home
    w+=win;l+=not win;pnl+=(o-1) if win else -1
rep("ML model-backed DOGS",w,l,pnl,be_=0.40)
# totals (need env-form; simple: fit tdev on prior, same expanding — quick version: pace features)
for r in rows:pass
w=l=0;pnl=0;wu=lu=0;pnlu=0
# expanding totals
predsT={}
for i,ssn in enumerate(seasons):
    prior=[r for r in rows if r['season']<ssn]
    if len(prior)<300:continue
    run=[f(r2['total']) or 0 for r2 in prior]
    env=statistics.mean(run[-60:])
    B=ols([[f(r2['pace_s']) or 0,f(r2['tov']) or 0,f(r2['p3pct']) or 0,1] for r2 in prior],
          [(f(r2['total']) or 0)-env for r2 in prior])
    for r2 in rows:
        if r2['season']==ssn:
            predsT[r2['game_id']]=env+sum(b*x for b,x in zip(B,[f(r2['pace_s']) or 0,f(r2['tov']) or 0,f(r2['p3pct']) or 0,1]))
for r,g,b,m in J:
    ou=f(b['total']);tot=(f(g['home_score']) or 0)+(f(g['away_score']) or 0)
    t=predsT.get(r['game_id'])
    if ou is None or t is None or tot==ou:continue
    e=t-ou
    if abs(e)<3:continue
    over=e>0
    o=f(b['ou_o']) if over else f(b['ou_u'])
    win=(tot>ou)==over
    if over:w+=win;l+=not win;pnl+=((o or 1.9)-1) if win else -1
    else:wu+=win;lu+=not win;pnlu+=((o or 1.9)-1) if win else -1
rep("TOTALS overs |e|>=3",w,l,pnl,be_=0.535)
rep("TOTALS unders |e|>=3",wu,lu,pnlu,be_=0.535)
