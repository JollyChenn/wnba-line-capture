# MECHANISM CHECKS on RAW PRODUCTION (law 6). No prices anywhere in this file.
import os
D=os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D,"xm_table.py"),encoding="utf-8").read())
import statistics, collections, math, random
random.seed(20260826)

def corr(a,b):
    n=len(a)
    if n<3: return None,None
    ma,mb=statistics.mean(a),statistics.mean(b)
    sa=math.sqrt(sum((x-ma)**2 for x in a)); sb=math.sqrt(sum((x-mb)**2 for x in b))
    if sa==0 or sb==0: return None,None
    r=sum((a[i]-ma)*(b[i]-mb) for i in range(n))/(sa*sb)
    return r, r*math.sqrt((n-2)/max(1e-12,1-r*r))
def rank(v):
    s=sorted(range(len(v)),key=lambda i:v[i]); out=[0.0]*len(v); i=0
    while i<len(s):
        j=i
        while j+1<len(s) and v[s[j+1]]==v[s[i]]: j+=1
        av=(i+j)/2.0+1
        for k in range(i,j+1): out[s[k]]=av
        i=j+1
    return out
def spear(a,b):
    return corr(rank(a),rank(b))

# realised game score
score={}
for g in load("data/games_2026.csv"):
    hs,as_=f(g.get("home_score")),f(g.get("away_score"))
    if hs is not None and as_ is not None: score[g.get("game_id")]=(hs,as_)

print("### M1  does the PINNACLE TOTAL MOVE 12h->6h predict the realised game score? ###")
xs=[];ys=[];zs=[]
for gid in set(r["gid"] for r in T):
    rows=[r for r in T if r["gid"]==gid]
    r0=rows[0]
    if r0["dtot"] is None or gid not in score: continue
    xs.append(r0["dtot"]); ys.append(sum(score[gid])); zs.append(r0["tot6"])
r,t=corr(xs,ys); print("  d_total(12->6) vs realised score : rho=%+.3f t=%+.2f n=%d"%(r,t,len(xs)))
r,t=corr(zs,ys); print("  total level @6h  vs realised score: rho=%+.3f t=%+.2f n=%d"%(r,t,len(zs)))
r,t=corr(xs,[ys[i]-zs[i] for i in range(len(xs))])
print("  d_total          vs (score - total): rho=%+.3f t=%+.2f  <- does the move add info?"%(r,t))
up=[ys[i]-zs[i] for i in range(len(xs)) if xs[i]>=1]; dn=[ys[i]-zs[i] for i in range(len(xs)) if xs[i]<=-1]
print("  mean(score-total) | total ROSE >=1  = %+.2f  (n=%d)"%(statistics.mean(up) if up else 0,len(up)))
print("  mean(score-total) | total FELL <=-1 = %+.2f  (n=%d)"%(statistics.mean(dn) if dn else 0,len(dn)))
print("")

print("### M2  does the total move predict PLAYER production vs her line? ###")
sub=[r for r in T if r["dtot"] is not None]
def z(r): return (r["actual"]-r["line"])/max(1.0,r["line"])**0.5
r,t=corr([x["dtot"] for x in sub],[z(x) for x in sub])
print("  all props            rho=%+.3f t=%+.2f n=%d"%(r,t,len(sub)))
s2=[x for x in sub if x["dline1"]==0.0]
r,t=corr([x["dtot"] for x in s2],[z(x) for x in s2])
print("  her line UNMOVED     rho=%+.3f t=%+.2f n=%d"%(r,t,len(s2)))
for lab,fl in (("totUP>=1",lambda x:x["dtot"]>=1),("totDN<=-1",lambda x:x["dtot"]<=-1),("flat",lambda x:abs(x["dtot"])<1)):
    v=[z(x) for x in sub if fl(x)]; w=[1 for x in sub if fl(x) and x["over_won"]]
    n=sum(1 for x in sub if fl(x))
    print("    %-10s n=%4d  mean z(actual-line)=%+.4f  over-rate=%.3f"%(lab,n,statistics.mean(v),len(w)/max(1,n)))
print("")

print("### M3  does the SPREAD widening predict blowouts, and blowouts suppress production? ###")
xs=[];ys=[]
for gid in set(r["gid"] for r in T):
    rows=[r for r in T if r["gid"]==gid]; r0=rows[0]
    if r0["dabsspr"] is None or gid not in score: continue
    xs.append(r0["dabsspr"]); ys.append(abs(score[gid][0]-score[gid][1]))
r,t=corr(xs,ys); print("  d|spread|(12->6) vs realised margin: rho=%+.3f t=%+.2f n=%d"%(r,t,len(xs)))
# blowout -> production
bl=[];nb=[]
for r_ in T:
    if r_["gid"] not in score: continue
    m=abs(score[r_["gid"]][0]-score[r_["gid"]][1])
    (bl if m>=15 else nb).append(z(r_))
print("  z(actual-line) in blowouts(>=15) = %+.4f n=%d ; close games = %+.4f n=%d"%(
      statistics.mean(bl),len(bl),statistics.mean(nb),len(nb)))
# star-specific
print("")
print("### M4  her own PTS line move -> her realised pts, and her realised pra ###")
ptsmove={}
for r_ in T:
    if r_["mk"]=="pts" and r_["dline1"] is not None: ptsmove[(r_["pl"],r_["gid"])]=r_["dline1"]
for tgt in ("pts","pra","pr","pa","reb","ast","ra"):
    sub=[r_ for r_ in T if r_["mk"]==tgt and (r_["pl"],r_["gid"]) in ptsmove]
    if len(sub)<50: continue
    xs=[ptsmove[(r_["pl"],r_["gid"])] for r_ in sub]; ys=[z(r_) for r_ in sub]
    r,t=corr(xs,ys)
    upn=[y for x,y in zip(xs,ys) if x>=1]; dnn=[y for x,y in zip(xs,ys) if x<=-1]
    print("  target %-4s n=%4d rho=%+.3f t=%+.2f | z|ptsUP=%+.3f (n=%d)  z|ptsDN=%+.3f (n=%d)"%(
        tgt,len(sub),r,t,statistics.mean(upn) if upn else float('nan'),len(upn),
        statistics.mean(dnn) if dnn else float('nan'),len(dnn)))
print("")
print("### M5  STEAM: does a pack move predict production better than a lone move? ###")
by_date=collections.defaultdict(list)
for r_ in T:
    if r_["dline1"] is not None: by_date[r_["date"]].append(r_)
for d,rows in by_date.items():
    ups=[x for x in rows if x["dline1"]>=1.0]; dns=[x for x in rows if x["dline1"]<=-1.0]
    for r_ in rows:
        r_["same_up"]=sum(1 for x in ups if x["pl"]!=r_["pl"])
        r_["same_dn"]=sum(1 for x in dns if x["pl"]!=r_["pl"])
S=[r_ for r_ in T if r_["dline1"] is not None]
for lab,fl in (("upPACK(>=3)",lambda x:x["dline1"]>=1 and x["same_up"]>=3),
               ("upALONE(<=1)",lambda x:x["dline1"]>=1 and x["same_up"]<=1),
               ("dnPACK(>=3)",lambda x:x["dline1"]<=-1 and x["same_dn"]>=3),
               ("dnALONE(<=1)",lambda x:x["dline1"]<=-1 and x["same_dn"]<=1),
               ("nomove",lambda x:x["dline1"]==0.0)):
    v=[z(x) for x in S if fl(x)]; o=[1 for x in S if fl(x) and x["over_won"]]
    if not v: continue
    print("  %-13s n=%4d  mean z=%+.4f  over-rate=%.3f"%(lab,len(v),statistics.mean(v),len(o)/len(v)))
print("")
print("### M6  DRIFT: 1xbet Over price move 12h->6h -> production ###")
S=[r_ for r_ in T if r_["dood1"] is not None]
xs=[r_["dood1"] for r_ in S]; ys=[z(r_) for r_ in S]
r,t=corr(xs,ys); print("  d_over_odds vs z(actual-line): rho=%+.3f t=%+.2f n=%d"%(r,t,len(S)))
for lab,fl in (("short(<=-.05)",lambda x:x["dood1"]<=-0.05),("long(>=+.05)",lambda x:x["dood1"]>=0.05),
               ("flat",lambda x:abs(x["dood1"])<0.05)):
    v=[z(x) for x in S if fl(x)]; o=[1 for x in S if fl(x) and x["over_won"]]
    if not v: continue
    print("  %-14s n=%4d mean z=%+.4f over-rate=%.3f"%(lab,len(v),statistics.mean(v),len(o)/len(v)))
