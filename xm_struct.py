# Final structural summary: who moves first, batch structure of the 1xbet prop board,
# and the isolated-vs-pack question answered at both slate and game level.
import os, functools
D=os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D,"xm_table.py"),encoding="utf-8").read())
print=functools.partial(print,flush=True)
import statistics, collections, math, random
random.seed(20260826)
H=lambda h: datetime.timedelta(hours=h)

print("### 1. how does the 1xbet prop board actually change? ###")
nchg=collections.Counter(); step=collections.Counter()
for (pl,mk,gid),s in PROP.items():
    ln=[x[1] for x in s["Over"]]
    ch=[(ln[i]-ln[i-1]) for i in range(1,len(ln)) if ln[i]!=ln[i-1]]
    nchg[len(ch)]+=1
    for c in ch: step[c]+=1
print("  line changes per player-market-game:",dict(sorted(nchg.items())[:6]))
print("  step sizes:",step.most_common(8))
# capture batching: do all moves in a slate land in the same capture?
bat=collections.defaultdict(set)
for (pl,mk,gid),s in PROP.items():
    prev=None
    for c,ln,od in s["Over"]:
        if prev is not None and ln!=prev: bat[c.replace(minute=0,second=0,microsecond=0)].add((pl,mk,gid))
        prev=ln
sz=sorted((len(v) for v in bat.values()),reverse=True)
print("  distinct capture-hours containing >=1 line move: %d ; moves per such hour: median %d, p90 %d, max %d"%(
    len(sz),sz[len(sz)//2],sz[int(.1*len(sz))],sz[0]))
print("")

print("### 2. isolated vs pack movers, slate level AND game level ###")
for r in T: r["same_up"]=0; r["same_dn"]=0; r["g_up"]=0; r["g_dn"]=0
byd=collections.defaultdict(list); byg=collections.defaultdict(list)
for r in T:
    if r["dline1"] is not None: byd[r["date"]].append(r); byg[r["gid"]].append(r)
for grp,ku,kd in ((byd,"same_up","same_dn"),(byg,"g_up","g_dn")):
    for k,rows in grp.items():
        ups=[x for x in rows if x["dline1"]>=1.0]; dns=[x for x in rows if x["dline1"]<=-1.0]
        for r in rows:
            r[ku]=sum(1 for x in ups if x["pl"]!=r["pl"]); r[kd]=sum(1 for x in dns if x["pl"]!=r["pl"])
mv=[r for r in T if r["dline1"] is not None and abs(r["dline1"])>=1.0]
print("  movers (12h->6h window): %d of %d rows"%(len(mv),sum(1 for r in T if r["dline1"] is not None)))
for lab,ku in (("slate","same_"),("game","g_")):
    lone=sum(1 for r in mv if (r[ku+"up"] if r["dline1"]>0 else r[ku+"dn"])<=1)
    print("  %-6s level: movers with <=1 other prop moving the same way: %d (%.1f%%)"%(lab,lone,100*lone/len(mv)))
print("")
def roi(rows,sd): return 100*statistics.mean(pnl(r,sd) for r in rows) if rows else float('nan')
def orate(rows): return sum(1 for r in rows if r["over_won"])/len(rows) if rows else float('nan')
print("  GAME-level isolated vs pack (Over side):")
for lab,fl in (("up, alone in game", lambda r:r["dline1"]>=1 and r["g_up"]==0),
               ("up, with teammates",lambda r:r["dline1"]>=1 and r["g_up"]>=1),
               ("dn, alone in game", lambda r:r["dline1"]<=-1 and r["g_dn"]==0),
               ("dn, with teammates",lambda r:r["dline1"]<=-1 and r["g_dn"]>=1)):
    v=[r for r in mv if fl(r)]
    if v: print("    %-20s n=%4d over%%=%.3f ROI_O=%+6.2f ROI_U=%+6.2f"%(lab,len(v),orate(v),roi(v,"Over"),roi(v,"Under")))
print("")

print("### 3. reaction speed of the 1xbet prop board to a >=1pt Pinnacle total move ###")
ev=collections.defaultdict(lambda:[0,0,0.0,0.0])
props_by_gid=collections.defaultdict(list)
for (pl,mk,gid) in PROP: props_by_gid[gid].append((pl,mk))
nev=0
for gid,ser in PT.items():
    tp=aware(gmeta[gid][1]); base=None; t0=None; d=0
    for c,p_,pr in ser:
        hh=(tp-c).total_seconds()/3600
        if hh>20 or hh<2: continue
        if base is None: base=p_; continue
        if abs(p_-base)>=1.0: t0=c; d=p_-base; break
    if t0 is None: continue
    nev+=1
    for (pl,mk) in props_by_gid[gid]:
        s=PROP[(pl,mk,gid)]["Over"]; pre=at_or_before(s,t0)
        if not pre: continue
        for tau in (1,2,3,6,12,999):
            w=t0+H(tau) if tau!=999 else tp
            post=at_or_before(s,w)
            if not post: continue
            e=ev[tau]; e[0]+=1
            if post[1]!=pre[1]: e[1]+=1
            e[2]+= (post[1]-pre[1])*(1 if d>0 else -1)   # move in the total's direction
            e[3]+= abs(post[1]-pre[1])
print("  %d total-move events (>=1.0 pt, between 20h and 2h before tip)"%nev)
print("  %-8s %6s %10s %16s"%("tau","n","pct moved","mean signed move (in the total's direction)"))
for tau in (1,2,3,6,12,999):
    e=ev[tau]
    if e[0]: print("  +%-7s %6d %9.1f%% %16.4f"%(("%dh"%tau) if tau!=999 else "tip",e[0],100*e[1]/e[0],e[2]/e[0]))
print("")
print("### 4. correlations worth recording ###")
def corr(a,b):
    n=len(a); ma,mb=statistics.mean(a),statistics.mean(b)
    sa=math.sqrt(sum((x-ma)**2 for x in a)); sb=math.sqrt(sum((x-mb)**2 for x in b))
    if sa==0 or sb==0: return None,None
    r=sum((a[i]-ma)*(b[i]-mb) for i in range(n))/(sa*sb)
    return r, r*math.sqrt((n-2)/max(1e-12,1-r*r))
score={}
for g in load("data/games_2026.csv"):
    hs,as_=f(g.get("home_score")),f(g.get("away_score"))
    if hs is not None and as_ is not None: score[g.get("game_id")]=(hs,as_)
gg={}
for r in T:
    if r["dtot"] is not None and r["gid"] in score: gg[r["gid"]]=(r["dtot"],r["tot6"],sum(score[r["gid"]]),r["dabsspr"])
xs=[v[0] for v in gg.values()]; ys=[v[2] for v in gg.values()]
r,t=corr(xs,ys); print("  Pinn total MOVE 12h->6h vs realised score : rho=%+.3f t=%+.2f n=%d"%(r,t,len(xs)))
r,t=corr([v[1] for v in gg.values()],ys); print("  Pinn total LEVEL @6h    vs realised score : rho=%+.3f t=%+.2f n=%d"%(r,t,len(xs)))
mg=[abs(score[g][0]-score[g][1]) for g in gg]; sp=[v[3] for v in gg.values()]
r,t=corr(sp,mg); print("  Pinn |spread| MOVE      vs realised margin: rho=%+.3f t=%+.2f n=%d"%(r,t,len(sp)))
S=[r_ for r_ in T if r_["dood1"] is not None]
def z(r_): return (r_["actual"]-r_["line"])/max(1.0,r_["line"])**0.5
r,t=corr([x["dood1"] for x in S],[z(x) for x in S]); print("  1xbet OVER-PRICE drift  vs z(actual-line) : rho=%+.3f t=%+.2f n=%d"%(r,t,len(S)))
P=[r_ for r_ in T if r_["mk"]=="pts" and r_["dline1"] is not None]
r,t=corr([x["dline1"] for x in P],[z(x) for x in P]); print("  her PTS line move       vs her pts z      : rho=%+.3f t=%+.2f n=%d"%(r,t,len(P)))
pm={(r_["pl"],r_["gid"]):r_["dline1"] for r_ in P}
O=[r_ for r_ in T if r_["mk"]!="pts" and (r_["pl"],r_["gid"]) in pm]
r,t=corr([pm[(x["pl"],x["gid"])] for x in O],[z(x) for x in O]); print("  her PTS line move       vs OTHER market z  : rho=%+.3f t=%+.2f n=%d"%(r,t,len(O)))
