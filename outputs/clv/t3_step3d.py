import csv,os,sys,statistics,collections,datetime
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
D=r"C:\Users\Axioo\wnba-line-capture"
def ts(s):
    s=(s or "").replace("Z","+00:00")
    try: return datetime.datetime.fromisoformat(s)
    except Exception: return None
GM=list(csv.DictReader(open(os.path.join(D,"data","games_2026.csv"),encoding="utf-8")))
tipof={g["game_id"]:ts(g["tip"]) for g in GM}; dateof={g["game_id"]:g["date"] for g in GM}
pl_game={}
for r in csv.DictReader(open(os.path.join(D,"data","box_2026.csv"),encoding="utf-8")):
    if r["game_id"] in dateof: pl_game[(r["player"].lower(),dateof[r["game_id"]])]=r["game_id"]
Q=collections.defaultdict(list)
for r in csv.DictReader(open(os.path.join(D,"xbet_board.csv"),encoding="utf-8")):
    t=ts(r["captured_utc"])
    if t: 
        try: Q[(r["player"].lower(),r["market"])].append((t,float(r["line"]),r["side"],float(r["odds"])))
        except: pass
for k in Q: Q[k].sort()
R=list(csv.DictReader(open(os.path.join(D,"graded_bets.csv"),encoding="utf-8")))
by=collections.defaultdict(list)
for r in R:
    gid=pl_game.get((r["player"].lower(),r["date"]))
    if not gid: continue
    tip=tipof[gid]; lo=tip-datetime.timedelta(hours=72)
    q=[x for x in Q.get((r["player"].lower(),r["market"]),()) if lo<x[0]<tip]
    if not q: continue
    by[r["date"][:6]].append((tip-q[-1][0]).total_seconds()/3600)
print("last 1xbet quote before tip, by month (graded-bet population)")
for m,v in sorted(by.items()):
    print(f"  {m} n={len(v):4d} median {statistics.median(v):6.2f}h   <2h {sum(1 for x in v if x<2)/len(v)*100:4.0f}%  <6h {sum(1 for x in v if x<6)/len(v)*100:4.0f}%")
