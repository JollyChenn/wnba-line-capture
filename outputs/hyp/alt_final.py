# STEP 2 (rigorous) + STEP 4 (graded, real prices, game-block bootstrap + noise ceiling)
import os,sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from _boot import ROOT, _src
exec(_src)
random.seed(20260826)
def vf(o,u): return (1.0/o)/((1.0/o)+(1.0/u))
def NCDF(z): return 0.5*(1+math.erf(z/math.sqrt(2)))
def NPDF(z): return math.exp(-0.5*z*z)/math.sqrt(2*math.pi)

rows = load("xbet_board.csv")
inst = collections.defaultdict(lambda: collections.defaultdict(dict))
for b in rows:
    t, o, ln = b.get("captured_utc"), f(b.get("odds")), f(b.get("line"))
    if not (t and o and ln is not None and b.get("market") in ALL_MK): continue
    inst[(_pl(b.get("player")), b.get("market"), t)][ln][b.get("side")] = o

LAD=[]
for (pl, mk, tstr), v in inst.items():
    rung = {ln: s for ln, s in v.items() if "Over" in s and "Under" in s}
    if len(rung) < 2: continue
    tm = teamof.get(pl)
    if not tm: continue
    t = ts(tstr); g2 = game_for(tm, t)
    if not g2: continue
    now = pgrow.get((pl, g2))
    if not now or now["min"] < 8: continue
    prior = [x for x in hist.get(pl, []) if x["tip"] < g2 and x["tm"] == now["tm"]]
    if len(prior) < 5: continue
    vals=[x[mk] for x in prior[-15:]]
    sd = statistics.pstdev(vals)
    if sd <= 0: continue
    LAD.append(dict(pl=pl,mk=mk,gt=g2,t=t,rung=rung,actual=now[mk],
                    hrs=(g2-t).total_seconds()/3600.0,mu=statistics.mean(vals),sd=sd,vals=vals))
# keep ONE instant per player-market-game: the LAST one before tip (gate & price same instant)
best={}
for r in LAD:
    k=(r["pl"],r["mk"],r["gt"])
    if k not in best or r["t"]>best[k]["t"]: best[k]=r
LADU=list(best.values())
print(f"unique player-market-games with a simultaneous ladder: {len(LADU)}  games={len(set(r['gt'] for r in LADU))}  players={len(set(r['pl'] for r in LADU))}")

print("\n"+"="*78); print("STEP 2  PRICING MODEL OF THE LADDER"); print("="*78)
recs=[]
for r in LADU:
    ks=sorted(r["rung"])
    a,b2=ks[0],ks[-1]; d=b2-a
    if d<=0: continue
    pa_=vf(r["rung"][a]["Over"],r["rung"][a]["Under"]); pb_=vf(r["rung"][b2]["Over"],r["rung"][b2]["Under"])
    slope=(pa_-pb_)/d
    mid=(a+b2)/2.0; z=(mid-r["mu"])/r["sd"]
    pred=NPDF(z)/r["sd"]                    # slope her OWN distribution implies
    emp=sum(1 for x in r["vals"] if a<x<=b2)/len(r["vals"])/d
    recs.append(dict(slope=slope,pred=pred,emp=emp,sd=r["sd"],mk=r["mk"],gt=r["gt"],pl=r["pl"],d=d,z=z))
print(f"n adjacent-rung pairs (one per player-market-game) = {len(recs)}, games={len(set(x['gt'] for x in recs))}")
S=[x["slope"] for x in recs]; P=[x["pred"] for x in recs]
print(f"  BOOK slope dP/dpt      median {statistics.median(S):+.4f}   mean {statistics.mean(S):+.4f}   sd {statistics.pstdev(S):.4f}")
print(f"  HER-DISTRIBUTION slope median {statistics.median(P):+.4f}   mean {statistics.mean(P):+.4f}")
print(f"  => implied POINTS per 1pp of probability: book {1/(100*statistics.median(S)):.2f} pts, fair {1/(100*statistics.median(P)):.2f} pts")
print(f"  ratio book/fair = {statistics.median(S)/statistics.median(P):.3f}  (1.0 = book matches her distribution)")

def spear(x,y):
    n=len(x); 
    def rk(a):
        o=sorted(range(n),key=lambda i:a[i]); r=[0.0]*n; i=0
        while i<n:
            j=i
            while j+1<n and a[o[j+1]]==a[o[i]]: j+=1
            av=(i+j)/2+1
            for k in range(i,j+1): r[o[k]]=av
            i=j+1
        return r
    rx,ry=rk(x),rk(y); mx=sum(rx)/n; my=sum(ry)/n
    nu=sum((p-mx)*(q-my) for p,q in zip(rx,ry))
    de=math.sqrt(sum((p-mx)**2 for p in rx)*sum((q-my)**2 for q in ry))
    return nu/de if de else 0.0
rho=spear(S,[x["sd"] for x in recs]); rho2=spear(P,[x["sd"] for x in recs])
# game-block permutation of the SD label
games=collections.defaultdict(list)
for i,x in enumerate(recs): games[x["gt"]].append(i)
gl=list(games)
null=[]
for _ in range(4000):
    perm=gl[:]; random.shuffle(perm)
    sdp=[0.0]*len(recs)
    for src,dst in zip(gl,perm):
        srcv=[recs[i]["sd"] for i in games[src]]; dstidx=games[dst]
        for j,i2 in enumerate(dstidx): sdp[i2]=srcv[j%len(srcv)]
    null.append(spear(S,sdp))
p_rho=sum(1 for x in null if abs(x)>=abs(rho))/len(null)
print(f"\n  Spearman(book slope, her SD)      = {rho:+.3f}   game-block perm p = {p_rho:.4f}")
print(f"  Spearman(fair  slope, her SD)      = {rho2:+.3f}   (the direction a modelled book MUST show)")
print("  -> a FIXED parametric shift would give rho = 0.00; a fully individual model would give ~%.2f" % rho2)
# fit quality: constant model vs proportional-to-fair model
mS=statistics.mean(S)
sst=sum((s-mS)**2 for s in S)
k=sum(s*p for s,p in zip(S,P))/sum(p*p for p in P)
sse=sum((s-k*p)**2 for s,p in zip(S,P))
print(f"\n  R^2 of 'book slope = k * her-distribution slope' (k={k:.3f}): {1-sse/sst:+.3f}")
print(f"     (<=0 means a single CONSTANT fits the ladder as well as any per-player model)")
print("\n  book slope by her-volatility quintile:")
qs=sorted(recs,key=lambda x:x["sd"]); n5=len(qs)//5
for i in range(5):
    s=qs[i*n5:(i+1)*n5] if i<4 else qs[4*n5:]
    print(f"    Q{i+1} sd {s[0]['sd']:.1f}-{s[-1]['sd']:.1f}  book {statistics.median([x['slope'] for x in s]):+.4f}"
          f"   fair {statistics.median([x['pred'] for x in s]):+.4f}   ratio {statistics.median([x['slope'] for x in s])/statistics.median([x['pred'] for x in s]):.2f}")
import json
json.dump([{k2:(v2 if not isinstance(v2,datetime.datetime) else v2.isoformat()) for k2,v2 in x.items()} for x in recs],
          open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"alt_slopes.json"),"w"))
