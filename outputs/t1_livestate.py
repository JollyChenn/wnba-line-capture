import csv, os, sys, datetime, collections, statistics
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
R=r"C:\Users\Axioo\wnba-line-capture"
def L(p): return list(csv.DictReader(open(os.path.join(R,p),encoding="utf-8",errors="replace")))
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z","+00:00"))
    except Exception: return None
LL=L("live_lines.csv"); LS=L("live_snapshots.csv"); GM=L("data/games_2026.csv")
print("live_lines",len(LL),"live_snapshots",len(LS))
FULL={"Atlanta Dream":"ATL","Chicago Sky":"CHI","Connecticut Sun":"CON","Dallas Wings":"DAL",
 "Golden State Valkyries":"GS","Indiana Fever":"IND","Los Angeles Sparks":"LA","Las Vegas Aces":"LV",
 "Minnesota Lynx":"MIN","New York Liberty":"NY","Phoenix Mercury":"PHX","Portland Fire":"POR",
 "Seattle Storm":"SEA","Toronto Tempo":"TOR","Washington Mystics":"WSH"}
# games with tip
tips={}
for g in GM:
    t=ts(g.get("tip"))
    if t: tips[g["game_id"]]=(t,g["home"],g["away"],g["date"],g.get("home_score"),g.get("away_score"))
# ---- live_lines: map each row to a game by team pair + ts within window
pair2gid=collections.defaultdict(list)
for gid,(t,h,a,d,hs,as_) in tips.items(): pair2gid[frozenset((h,a))].append((t,gid))
inplay=0; pregame=0; unmapped=0; gids=collections.Counter(); rowsby=collections.defaultdict(list)
for r in LL:
    t=ts(r["ts"]); tm=(r.get("teams") or "").split("|")
    if not t or len(tm)!=2: unmapped+=1; continue
    key=frozenset(FULL.get(x,x) for x in tm)
    cand=pair2gid.get(key,[])
    best=None
    for tp,gid in cand:
        if -12*3600 <= (t-tp).total_seconds() <= 4*3600: best=(tp,gid); break
    if not best: unmapped+=1; continue
    tp,gid=best
    if t>=tp: inplay+=1; gids[gid]+=1; rowsby[gid].append((t,r))
    else: pregame+=1
print(f"live_lines mapped: inplay={inplay} pregame={pregame} unmapped={unmapped}  distinct in-play games={len(gids)}")
# ---- live_snapshots coverage
sg=collections.Counter(r["game_id"] for r in LS)
print(f"live_snapshots distinct game_id={len(sg)} rows={len(LS)}")
print("  period non-null:",sum(1 for r in LS if r.get('period')), " clock:",sum(1 for r in LS if r.get('clock')),
      " scores:",sum(1 for r in LS if r.get('home_score') not in ("",None)))
ov=set(sg)&set(gids)
print(f"  OVERLAP with live_lines in-play games: {len(ov)} of {len(gids)}")
print("  snapshot games:",sorted(sg)[:40])
print("  odds games    :",sorted(gids)[:40])
# per overlapping game: how many odds rows can be matched to a snapshot within 90s?
if ov:
    snapby=collections.defaultdict(list)
    for r in LS:
        t=ts(r["ts"])
        if t: snapby[r["game_id"]].append((t,r))
    for v in snapby.values(): v.sort()
    tot=0; hit=0; gaps=[]
    for gid in ov:
        sn=snapby[gid]
        for t,r in rowsby[gid]:
            tot+=1
            d=min(abs((t-st).total_seconds()) for st,_ in sn)
            gaps.append(d)
            if d<=90: hit+=1
    print(f"  odds rows in overlapping games={tot}, matched to a snapshot within 90s={hit} ({100*hit/tot:.1f}%)")
    print(f"  median |dt| to nearest snapshot = {statistics.median(gaps):.0f}s")
    # snapshot cadence
    for gid in sorted(ov)[:6]:
        sn=snapby[gid]; ds=[(sn[i+1][0]-sn[i][0]).total_seconds() for i in range(len(sn)-1)]
        print(f"    {gid}: {len(sn)} snaps, median gap {statistics.median(ds)/60:.1f} min" if ds else f"    {gid}: {len(sn)} snaps")
# elo plays overlap
pg=set()
for r in csv.DictReader(open(os.path.join(R,"elo_model","plays_full.csv"),encoding="utf-8",errors="replace")):
    pg.add(r["game_id"])
print(f"plays_full distinct games={len(pg)}; overlap with live-odds games={len(pg&set(gids))}; overlap with live_snapshots={len(pg&set(sg))}")
