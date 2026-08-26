import csv, os, sys, datetime, collections, statistics
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
R = os.path.dirname(D)

FULL = {"Atlanta Dream":"ATL","Chicago Sky":"CHI","Connecticut Sun":"CON","Dallas Wings":"DAL",
 "Golden State Valkyries":"GS","Indiana Fever":"IND","Las Vegas Aces":"LV","Los Angeles Sparks":"LA",
 "Minnesota Lynx":"MIN","New York Liberty":"NY","Phoenix Mercury":"PHX","Seattle Storm":"SEA",
 "Washington Mystics":"WSH"}

def T(s):
    s=s.replace("Z","").replace("+00:00","")
    for f in ("%Y-%m-%dT%H:%M:%S","%Y-%m-%dT%H:%M"):
        try: return datetime.datetime.strptime(s,f)
        except Exception: pass
    return None

games={}
for g in csv.DictReader(open(os.path.join(R,"data","games_2026.csv"),encoding="utf-8")):
    tp=T(g["tip"])
    if tp: games[g["game_id"]]=(tp,g["home"],g["away"],g.get("home_score"),g.get("away_score"))

snaps=collections.defaultdict(list)
allsnap=[]
for s in csv.DictReader(open(os.path.join(R,"live_snapshots.csv"),encoding="utf-8")):
    t=T(s["ts"])
    if t: snaps[s["game_id"]].append((t,s)); allsnap.append((t,s))
for k in snaps: snaps[k].sort(key=lambda x:x[0])
snap_games=set(snaps)
snap_ts=sorted(set(t for t,_ in allsnap))

# ---- build in-play odds set by (teams -> game, ts in window) ----
WIN=datetime.timedelta(hours=3)
byteams=collections.defaultdict(list)
for gid,(tp,h,a,hs,as_) in games.items(): byteams[frozenset([h,a])].append((tp,gid))

inplay=[]; unmapped=0
for r in csv.DictReader(open(os.path.join(R,"live_lines.csv"),encoding="utf-8")):
    t=T(r["ts"])
    parts=r["teams"].split("|")
    ab=[FULL.get(p.strip()) for p in parts]
    if not t or None in ab or len(ab)!=2: unmapped+=1; continue
    cand=byteams.get(frozenset(ab),[])
    hit=None
    for tp,gid in cand:
        if tp<=t<=tp+WIN: hit=gid; break
    if hit: inplay.append((t,hit,r))

ipg=set(g for _,g,_ in inplay)
print("=== IN-PLAY RECONSTRUCTION ===")
print("unmapped team rows:", unmapped)
print("in-play odds rows:", len(inplay), " independent games:", len(ipg))
print("snapshot games:", len(snap_games))
print("in-play games WITHOUT snapshots:", sorted(ipg-snap_games))
print("snapshot games WITHOUT in-play odds:", sorted(snap_games-ipg))

# ---- JOIN TEST A: correct per-game join ----
def nearest(lst,t):
    best=None
    for st,s in lst:
        d=abs((st-t).total_seconds())
        if best is None or d<best[0]: best=(d,s)
    return best

dts=[]; matched90=0; exact=0
for t,gid,r in inplay:
    b=nearest(snaps.get(gid,[]),t)
    if b is None: dts.append(None); continue
    dts.append(b[0])
    if b[0]<=90: matched90+=1
    if b[0]==0: exact+=1
ok=[d for d in dts if d is not None]
print("\n=== JOIN A: per-game (ts + game_id) ===")
print("matched<=90s: %d / %d = %.2f%%"%(matched90,len(inplay),100*matched90/len(inplay)))
print("exact ts match: %.2f%%"%(100*exact/len(inplay)))
print("median |dt| s:", statistics.median(ok), " p90:", sorted(ok)[int(.9*len(ok))])

# ---- JOIN TEST B: ts-only (game-blind) -> does 'identical ts' do the work? ----
si=0; m90b=0
sset=snap_ts
import bisect
for t,gid,r in inplay:
    i=bisect.bisect_left(sset,t)
    best=min([abs((sset[j]-t).total_seconds()) for j in (i-1,i,i+1) if 0<=j<len(sset)])
    if best<=90: m90b+=1
print("\n=== JOIN B: ts-only, GAME-BLIND (false-join control) ===")
print("matched<=90s: %.2f%%  <- if ~equal to A, ts alone is NOT evidence of a same-game join"%(100*m90b/len(inplay)))

# ---- CROSS-GAME CONTAMINATION: at an odds row's ts, how many OTHER games have a snap? ----
tsidx=collections.defaultdict(set)
for t,s in allsnap: tsidx[t].add(s["game_id"])
multi=collections.Counter()
for t,gid,r in inplay:
    multi[len(tsidx.get(t,()))]+=1
print("games present in snapshot file at the odds row's exact ts:", dict(sorted(multi.items())))

# ---- TRUNCATION / COVERAGE ----
print("\n=== COVERAGE / TRUNCATION ===")
q1=q4=0; complete=0; startgap=[]; endgap=[]
for gid,lst in snaps.items():
    pers=[s["period"] for _,s in lst]
    if "1" in pers: q1+=1
    if any(p in ("4","5","6") for p in pers): q4+=1
    tp=games.get(gid,(None,))[0]
    if tp: startgap.append((lst[0][0]-tp).total_seconds()/60.0)
    # final reached? last snap score vs final box
    g=games.get(gid)
    if g and g[3] and g[4]:
        try:
            fh,fa=float(g[3]),float(g[4])
            lh,la=float(lst[-1][1]["home_score"]),float(lst[-1][1]["away_score"])
            if lh==fh and la==fa: complete+=1
            endgap.append((fh+fa)-(lh+la))
        except Exception: pass
print("games w/ a Q1 row: %d/27   games reaching Q4+: %d/27"%(q1,q4))
print("games whose LAST snapshot equals the FINAL score (complete trace): %d/27"%complete)
print("median points of the game MISSING after last snapshot:", statistics.median(endgap) if endgap else "n/a")
print("median minutes from tip to FIRST snapshot:", round(statistics.median(startgap),1) if startgap else "n/a")

# ---- STATE INTEGRITY (is the joined state usable / monotone?) ----
print("\n=== STATE INTEGRITY ===")
bad=0; tot=0; dupclock=0
for gid,lst in snaps.items():
    prev=None
    for t,s in lst:
        tot+=1
        try: cur=(int(s["period"]), float(s["home_score"])+float(s["away_score"]))
        except Exception: bad+=1; continue
        if prev and (cur[0]<prev[0] or cur[1]<prev[1]): bad+=1
        prev=cur
print("non-monotone/unparseable state rows: %d / %d (%.1f%%)"%(bad,tot,100*bad/tot))

# effective sample: distinct STATE changes, not odds rows
states=set()
for t,gid,r in inplay:
    b=nearest(snaps.get(gid,[]),t)
    if b: states.add((gid,b[1]["period"],b[1]["clock"],b[1]["home_score"],b[1]["away_score"]))
print("distinct (game,period,clock,score) states behind %d odds rows: %d"%(len(inplay),len(states)))
print("design effect (odds rows per distinct state): %.1f"%(len(inplay)/max(1,len(states))))
