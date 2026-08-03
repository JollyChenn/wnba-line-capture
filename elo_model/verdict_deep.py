# rigorous follow-up on the two survivors: ML-dogs (+18.6u) and ATS-fav-side (57.5%)
import csv,math,statistics
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
    if t:be[(r['season'],t[0],t[1],r['hscore'],r['ascore'])]=r
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
preds={}
seasons=sorted({r['season'] for r in rows})
for ssn in seasons:
    prior=[r for r in rows if r['season']<ssn]
    if len(prior)<300:continue
    B=ols([[f(r[k]) or 0 for k in V]+[1] for r in prior],[f(r['margin']) or 0 for r in prior])
    for r in rows:
        if r['season']==ssn:preds[r['game_id']]=sum(b*(f(r[k]) or 0) for b,k in zip(B,V))+B[-1]
J=[]
for r in rows:
    gid=r['game_id']
    if gid not in preds:continue
    g=games[gid]
    b=be.get((g['season'],g['home'],g['away'],str(int(f(g['home_score']) or 0)),str(int(f(g['away_score']) or 0))))
    if b:J.append((r,g,b,preds[gid]))
def tstat(rets):
    n=len(rets);m=statistics.mean(rets);s=statistics.pstdev(rets)
    return m,m*n,m/(s/math.sqrt(n)) if s else 0
# ---- ML dogs ----
print("=== ML MODEL-BACKED DOGS ===")
by_season={};allr=[];odds_buckets={}
for r,g,b,m in J:
    oh,oa=f(b['ml_h']),f(b['ml_a'])
    if not oh or not oa:continue
    marg=(f(g['home_score']) or 0)-(f(g['away_score']) or 0)
    dog_home=oh>oa
    if (m>0)!=dog_home:continue
    o=oh if dog_home else oa
    ret=(o-1) if ((marg>0)==dog_home) else -1
    allr.append(ret);by_season.setdefault(g['season'],[]).append(ret)
    bk='2.0-2.5' if o<2.5 else ('2.5-3.5' if o<3.5 else '3.5+')
    odds_buckets.setdefault(bk,[]).append(ret)
m,tot,t=tstat(allr)
print(f"ALL: n={len(allr)} ROI={100*m:+.1f}% P&L={tot:+.1f}u t={t:+.2f}")
for s in sorted(by_season):
    m2,tot2,t2=tstat(by_season[s])
    print(f"  {s}: n={len(by_season[s]):>3} ROI={100*m2:+6.1f}% P&L={tot2:+6.1f}u")
for bk in sorted(odds_buckets):
    m3,tot3,_=tstat(odds_buckets[bk])
    print(f"  odds {bk}: n={len(odds_buckets[bk]):>3} ROI={100*m3:+6.1f}% P&L={tot3:+6.1f}u")
# ---- ATS fav side ----
print("\n=== ATS FAV-SIDE (edge>=2) ===")
by_s={};allf=[]
for r,g,b,m in J:
    sp=f(b['spread']);marg=(f(g['home_score']) or 0)-(f(g['away_score']) or 0)
    if sp is None:continue
    e=m+sp
    if abs(e)<2 or marg+sp==0:continue
    home=e>0
    if (sp>0)==home:continue   # dog side -> skip
    o=f(b['sp_h']) if home else f(b['sp_a'])
    ret=((o or 1.9)-1) if ((marg+sp>0)==home) else -1
    allf.append(ret);by_s.setdefault(g['season'],[]).append(ret)
m,tot,t=tstat(allf)
print(f"ALL: n={len(allf)} ROI={100*m:+.1f}% P&L={tot:+.1f}u t={t:+.2f}")
for s in sorted(by_s):
    m2,tot2,_=tstat(by_s[s])
    print(f"  {s}: n={len(by_s[s]):>3} ROI={100*m2:+6.1f}% P&L={tot2:+6.1f}u")
