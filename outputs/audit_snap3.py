import csv, os, sys, datetime, collections, statistics, bisect
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FULL = {"Atlanta Dream":"ATL","Chicago Sky":"CHI","Connecticut Sun":"CON","Dallas Wings":"DAL",
 "Golden State Valkyries":"GS","Indiana Fever":"IND","Las Vegas Aces":"LV","Los Angeles Sparks":"LA",
 "Minnesota Lynx":"MIN","New York Liberty":"NY","Phoenix Mercury":"PHX","Seattle Storm":"SEA",
 "Washington Mystics":"WSH","Portland Fire":"POR","Toronto Tempo":"TOR"}
def T(s):
    s=s.replace("Z","")
    for f in ("%Y-%m-%dT%H:%M:%S","%Y-%m-%dT%H:%M"):
        try: return datetime.datetime.strptime(s,f)
        except Exception: pass
    return None
games={}; byteams=collections.defaultdict(list)
for g in csv.DictReader(open(os.path.join(R,"data","games_2026.csv"),encoding="utf-8")):
    tp=T(g["tip"])
    if tp:
        games[g["game_id"]]=(tp,g["home"],g["away"])
        byteams[frozenset([g["home"],g["away"]])].append((tp,g["game_id"]))
snaps=collections.defaultdict(list)
for s in csv.DictReader(open(os.path.join(R,"live_snapshots.csv"),encoding="utf-8")):
    t=T(s["ts"]);  snaps[s["game_id"]].append((t,s))
for k in snaps: snaps[k].sort(key=lambda x:x[0])

WIN=datetime.timedelta(hours=3); inplay=[]; unmapped=0
for r in csv.DictReader(open(os.path.join(R,"live_lines.csv"),encoding="utf-8")):
    t=T(r["ts"]); ab=[FULL.get(p.strip()) for p in r["teams"].split("|")]
    if not t or None in ab or len(ab)!=2: unmapped+=1; continue
    for tp,gid in byteams.get(frozenset(ab),[]):
        if tp<=t<=tp+WIN: inplay.append((t,gid,r)); break
ipg=set(g for _,g,_ in inplay)
print("=== EXACT RECONSTRUCTION (full team map) ===")
print("unmapped rows:",unmapped,"| in-play odds rows:",len(inplay),"| independent games:",len(ipg))
print("in-play games lacking snapshots:",sorted(ipg-set(snaps)))

m90=0; ex=0; dts=[]
for t,gid,r in inplay:
    lst=snaps.get(gid,[])
    if not lst: continue
    tl=[x[0] for x in lst]; i=bisect.bisect_left(tl,t)
    d=min(abs((tl[j]-t).total_seconds()) for j in (i-1,i,i+1) if 0<=j<len(tl))
    dts.append(d)
    if d<=90: m90+=1
    if d==0: ex+=1
print("matched<=90s: %d / %d = %.2f%%   exact-ts: %.2f%%   median|dt|=%.0fs"%(
    m90,len(inplay),100*m90/len(inplay),100*ex/len(inplay),statistics.median(dts)))

print("\n=== LEAKAGE TEST: is game-clock ever AHEAD of wall-clock? ===")
viol=0; tot=0; lags=[]
for gid,lst in snaps.items():
    tp=games.get(gid,(None,))[0]
    if not tp: continue
    for t,s in lst:
        try:
            mm,ss=s["clock"].split(":"); rem=int(mm)*60+float(ss)
        except Exception: continue
        p=int(s["period"])
        elapsed_game = (min(p,4)-1)*600 + (600-rem) if p<=4 else 2400+(p-4)*300+(300-rem)
        elapsed_wall = (t-tp).total_seconds()
        tot+=1; lags.append(elapsed_wall-elapsed_game)
        if elapsed_game > elapsed_wall + 60: viol+=1
print("rows where game-clock EXCEEDS wall-clock (look-ahead signature): %d / %d"%(viol,tot))
print("median wall-minus-game elapsed: %.1f min (positive = normal stoppage+lag)"%(statistics.median(lags)/60))
print("min wall-minus-game: %.1f min"%(min(lags)/60))

print("\n=== EFFECTIVE SAMPLE BEHIND THE 24k ===")
states=set(); pergame=collections.Counter()
for t,gid,r in inplay:
    lst=snaps.get(gid,[])
    if not lst: continue
    tl=[x[0] for x in lst]; i=bisect.bisect_left(tl,t)
    j=min((jj for jj in (i-1,i,i+1) if 0<=jj<len(tl)),key=lambda jj:abs((tl[jj]-t).total_seconds()))
    s=lst[j][1]; key=(gid,s["period"],s["clock"],s["home_score"],s["away_score"])
    states.add(key); pergame[gid]+=1
print("odds rows: %d | distinct joined game-states: %d | independent games: %d"%(len(inplay),len(states),len(ipg)))
print("design effect (odds rows per distinct state): %.1f"%(len(inplay)/len(states)))
print("distinct states PER GAME: median %.0f"%statistics.median(collections.Counter(
    k[0] for k in states).values()))
