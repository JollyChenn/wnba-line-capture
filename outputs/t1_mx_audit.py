# Adversarial verification of the "live game state is joinable" audit claim.
import csv, os, sys, datetime, collections, statistics, random, math
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
R = r"C:\Users\Axioo\wnba-line-capture"
def L(p): return list(csv.DictReader(open(os.path.join(R,p),encoding="utf-8",errors="replace")))
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z","+00:00"))
    except Exception: return None

LL=L("live_lines.csv"); LS=L("live_snapshots.csv"); GM=L("data/games_2026.csv")
print("=== A. CENSUS ===")
print("live_lines rows:",len(LL),"  live_snapshots rows:",len(LS))
raw_ls=sum(1 for _ in open(os.path.join(R,"live_snapshots.csv"),encoding="utf-8",errors="replace"))
print("live_snapshots raw file lines (incl header):",raw_ls)
seen=set(); dup=0
cols=list(LS[0].keys())
for r in LS:
    k=tuple(r.get(c,"") for c in cols)
    if k in seen: dup+=1
    seen.add(k)
print("exact duplicate snapshot rows:",dup,"  unique:",len(seen))
tg=collections.Counter((r["ts"],r["game_id"]) for r in LS)
print("dup (ts,game_id) keys:",sum(v-1 for v in tg.values() if v>1))
sg=collections.Counter(r["game_id"] for r in LS)
print("distinct snapshot game_id:",len(sg))
nn=lambda c: sum(1 for r in LS if (r.get(c) or "").strip()!="")
for c in ["period","clock","away_score","home_score","h_fouls","a_fouls","h_to","a_to","h_reb","a_reb","last_play"]:
    print("   non-empty %-12s: %5d / %d" % (c, nn(c), len(LS)))

FULL={"Atlanta Dream":"ATL","Chicago Sky":"CHI","Connecticut Sun":"CON","Dallas Wings":"DAL",
 "Golden State Valkyries":"GS","Indiana Fever":"IND","Los Angeles Sparks":"LA","Las Vegas Aces":"LV",
 "Minnesota Lynx":"MIN","New York Liberty":"NY","Phoenix Mercury":"PHX","Portland Fire":"POR",
 "Seattle Storm":"SEA","Toronto Tempo":"TOR","Washington Mystics":"WSH"}
tips={}
for g in GM:
    t=ts(g.get("tip"))
    if t: tips[g["game_id"]]=(t,g["home"],g["away"],g["date"])
pair2=collections.defaultdict(list)
for gid,(t,h,a,d) in tips.items(): pair2[frozenset((h,a))].append((t,gid))

print()
print("=== B. INDEPENDENT MAPPING OF live_lines -> game ===")
inplay=collections.defaultdict(list); pre=0; unmapped=0; badteam=set()
for r in LL:
    t=ts(r["ts"]); tm=(r.get("teams") or "").split("|")
    if not t or len(tm)!=2: unmapped+=1; continue
    for x in tm:
        if x not in FULL: badteam.add(x)
    key=frozenset(FULL.get(x,x) for x in tm)
    best=None
    for tp,gid in pair2.get(key,[]):
        if -12*3600 <= (t-tp).total_seconds() <= 6*3600: best=(tp,gid); break
    if not best: unmapped+=1; continue
    tp,gid=best
    if t>=tp: inplay[gid].append((t,r))
    else: pre+=1
tot_inplay=sum(len(v) for v in inplay.values())
print("mapped in-play(t>=tip) rows:",tot_inplay,"  pregame:",pre,"  unmapped:",unmapped)
print("distinct in-play games:",len(inplay))
print("unmapped team strings:",sorted(badteam)[:10])

snapby=collections.defaultdict(list)
for r in LS:
    t=ts(r["ts"])
    if t: snapby[r["game_id"]].append((t,r))
for v in snapby.values(): v.sort()
ov=set(snapby)&set(inplay)
print("game_id overlap snapshots vs in-play-odds games:",len(ov),"of",len(inplay))
print("snapshot-only games:",sorted(set(snapby)-set(inplay)))
print("odds-only games   :",sorted(set(inplay)-set(snapby)))

print()
print("=== C. JOIN RATE (same game_id, |dt|<=90s) ===")
rows=[]
for gid in sorted(inplay):
    sn=snapby.get(gid,[])
    for t,r in inplay[gid]:
        if not sn: rows.append((gid,t,r,None,None)); continue
        b=min(sn,key=lambda x: abs((t-x[0]).total_seconds()))
        rows.append((gid,t,r,abs((t-b[0]).total_seconds()),b[1]))
hit=sum(1 for x in rows if x[3] is not None and x[3]<=90)
print("in-play odds rows=%d  matched<=90s=%d  (%.2f%%)" % (len(rows),hit,100.0*hit/len(rows)))
d0=sum(1 for x in rows if x[3]==0)
print("   exact dt=0s matches: %d (%.2f%%)" % (d0, 100.0*d0/len(rows)))
gaps=[x[3] for x in rows if x[3] is not None]
print("   median |dt|:",statistics.median(gaps),"s  p90:",sorted(gaps)[int(.9*len(gaps))],"  max:",max(gaps))

print()
print("=== D. STRATIFIED JOIN RATE ===")
def strat(name, keyf):
    d=collections.defaultdict(lambda:[0,0])
    for gid,t,r,dt,sn in rows:
        k=keyf(gid,t,r,dt,sn); d[k][0]+=1
        if dt is not None and dt<=90: d[k][1]+=1
    print("-- by "+name)
    for k in sorted(d, key=lambda z:-d[z][0])[:12]:
        n,h=d[k]; print("     %-28s n=%6d match=%6d %6.2f%%" % (str(k)[:28],n,h,100.0*h/n))
strat("market type", lambda g,t,r,dt,sn: r["type"])
strat("alt flag",    lambda g,t,r,dt,sn: r["alt"])
strat("period of matched snapshot", lambda g,t,r,dt,sn: (sn.get("period","?") if (sn and dt is not None and dt<=90) else "unmatched"))
strat("mins since tip", lambda g,t,r,dt,sn: "%03d-%03dm" % (int((t-tips[g][0]).total_seconds()//1800)*30, int((t-tips[g][0]).total_seconds()//1800)*30+30))

print("-- per game")
pg=collections.defaultdict(lambda:[0,0])
for gid,t,r,dt,sn in rows:
    pg[gid][0]+=1
    if dt is not None and dt<=90: pg[gid][1]+=1
worst=sorted(pg.items(), key=lambda kv: kv[1][1]/float(kv[1][0]))
for gid,(n,h) in worst[:8]+worst[-3:]:
    print("     %s n=%5d match=%5d %6.2f%%  snaps=%d" % (gid,n,h,100.0*h/n,len(snapby.get(gid,[]))))

print()
print("=== E. NOVELTY / OVERLAP WITH THE 4 LIVE EFFECTS ===")
GB=L("graded_bets.csv")
betdates=collections.Counter(r["date"] for r in GB)
gd={gid:tips[gid][3] for gid in inplay}
withbet=set(g for g in inplay if betdates.get(gd[g],0)>0)
print("in-play games whose DATE has >=1 graded prop bet:",len(withbet),"of",len(inplay))
for lab,S in [("date-has-bet",withbet),("date-no-bet",set(inplay)-withbet)]:
    n=h=0
    for gid,t,r,dt,sn in rows:
        if gid in S:
            n+=1
            if dt is not None and dt<=90: h+=1
    if n: print("     %-14s games=%3d n=%6d match=%6.2f%%" % (lab,len(S),n,100.0*h/n))

print()
print("=== F. COVERAGE DEPTH ===")
cnt=sorted(len(v) for v in snapby.values())
print("snaps/game: n=",len(cnt)," min",cnt[0]," med",statistics.median(cnt)," max",cnt[-1])
def sec(c):
    try:
        m,s=c.split(":"); return int(m)*60+float(s)
    except Exception: return None
q1=q4=comp=0; startp=collections.Counter(); endp=collections.Counter()
for gid,sn in snapby.items():
    ps=[int(r["period"]) for _,r in sn if (r.get("period") or "").isdigit()]
    if not ps: continue
    startp[ps[0]]+=1; endp[max(ps)]+=1
    if 1 in ps: q1+=1
    if max(ps)>=4: q4+=1
    first=sn[0][1]; last=sn[-1][1]
    fs=sec(first.get("clock","")); ls_=sec(last.get("clock",""))
    if ps[0]==1 and fs is not None and fs>=9*60 and max(ps)>=4 and ls_ is not None and ls_<=1.0: comp+=1
print("games containing a Q1 row:",q1,"  reaching period>=4:",q4,"  complete tip-to-final trace:",comp)
print("first-seen period histogram:",dict(sorted(startp.items())))
print("max period histogram      :",dict(sorted(endp.items())))
cad=[]
for sn in snapby.values():
    for i in range(len(sn)-1): cad.append((sn[i+1][0]-sn[i][0]).total_seconds())
print("snapshot cadence median:",statistics.median(cad),"s  p90:",sorted(cad)[int(.9*len(cad))],"s  max:",max(cad),"s")

print()
print("=== G. SAME-POLLER CHECK ===")
tl=sorted(set(r["ts"] for r in LL)); tsn=sorted(set(r["ts"] for r in LS))
print("distinct ts in live_lines:",len(tl),"first",tl[0],"last",tl[-1])
print("distinct ts in live_snaps:",len(tsn),"first",tsn[0],"last",tsn[-1])
print("snapshot ts also in live_lines:",len(set(tsn)&set(tl)),"/",len(tsn))
print("live_lines ts also in snapshots:",len(set(tl)&set(tsn)),"/",len(tl))

print()
print("=== H. IS THE JOINED STATE INFORMATIVE? ===")
stale=0; tot=0; nonmono=0
for gid,sn in snapby.items():
    prev=None
    for t,r in sn:
        cur=(r.get("period"),r.get("clock"),r.get("away_score"),r.get("home_score"))
        if prev is not None:
            tot+=1
            if cur==prev: stale+=1
            try:
                if int(r["away_score"])<int(prev[2]) or int(r["home_score"])<int(prev[3]): nonmono+=1
            except Exception: pass
        prev=cur
print("consecutive snapshots identical (period,clock,score): %d/%d (%.1f%%)" % (stale,tot,100.0*stale/tot))
print("score DECREASES between consecutive snapshots:",nonmono)
ds=[len(set((r.get("period"),r.get("clock")) for _,r in sn)) for sn in snapby.values()]
print("distinct (period,clock) states per game: med",statistics.median(ds),"min",min(ds),"max",max(ds))

print()
print("=== I. DESIGN EFFECT ===")
def deff(series):
    xs=[];ys=[]
    use=[s for s in series if len(s)>=3]
    for s in use:
        mu=statistics.mean(s); d=[v-mu for v in s]
        xs+=d[:-1]; ys+=d[1:]
    if len(xs)<10: return None,None,None
    mx=statistics.mean(xs); my=statistics.mean(ys)
    num=sum((a-mx)*(b-my) for a,b in zip(xs,ys))
    den=math.sqrt(sum((a-mx)**2 for a in xs)*sum((b-my)**2 for b in ys))
    rho=num/den if den else 0.0
    m=statistics.mean([len(s) for s in use])
    return rho,m,1+(m-1)*rho
for mkt in ["total","spread","moneyline"]:
    ser=[]
    for gid in inplay:
        s=[]
        for t,r in sorted(inplay[gid], key=lambda z:z[0]):
            if r["type"]==mkt and r["alt"]=="0":
                try:
                    s.append(float(r["points"]) if r["points"] else float(r["prices"].split(",")[0]))
                except Exception: pass
        if s: ser.append(s)
    rho,m,de=deff(ser)
    if de: print("   %-10s games=%d mean len=%.0f lag1 rho=%.3f design effect=%.1f n_eff~%.0f" % (mkt,len(ser),m,rho,de,sum(len(s) for s in ser)/de))

print()
print("=== J. plays_full overlap (control) ===")
pgset=set()
for r in csv.DictReader(open(os.path.join(R,"elo_model","plays_full.csv"),encoding="utf-8",errors="replace")):
    pgset.add(r.get("game_id"))
print("plays_full games:",len(pgset),"  overlap with in-play-odds games:",len(pgset&set(inplay)),
      "  overlap with snapshot games:",len(pgset&set(snapby)))
