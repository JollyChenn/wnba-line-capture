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
Q=collections.defaultdict(list)  # (player,market) -> [(t,line,side,odds)]
for r in csv.DictReader(open(os.path.join(D,"xbet_board.csv"),encoding="utf-8")):
    t=ts(r["captured_utc"])
    if not t: continue
    try: Q[(r["player"].lower(),r["market"])].append((t,float(r["line"]),r["side"],float(r["odds"])))
    except: pass
for k in Q: Q[k].sort()
R=list(csv.DictReader(open(os.path.join(D,"graded_bets.csv"),encoding="utf-8")))
lag1=[];lag2=[];mk=collections.Counter();lagm=collections.defaultdict(list)
for r in R:
    gid=pl_game.get((r["player"].lower(),r["date"]))
    if not gid: continue
    tip=tipof[gid]; lo=tip-datetime.timedelta(hours=72)
    q=[x for x in Q.get((r["player"].lower(),r["market"]),()) if lo<x[0]<tip]
    if not q: mk[r["market"]+"_none"]+=1; continue
    lag1.append((tip-q[-1][0]).total_seconds()/3600)
    lagm[r["market"]].append((tip-q[-1][0]).total_seconds()/3600)
    # two-sided
    bysnap=collections.defaultdict(dict)
    for t,ln,s,o in q: bysnap[(t,ln)][s]=o
    ts2=[k[0] for k,v in bysnap.items() if "Over" in v and "Under" in v]
    if ts2: lag2.append((tip-max(ts2)).total_seconds()/3600)
print(f"graded-bet population: last ANY quote before tip  n={len(lag1)} median {statistics.median(lag1):.2f}h  <2h {sum(1 for x in lag1 if x<2)/len(lag1)*100:.0f}%")
print(f"graded-bet population: last TWO-SIDED before tip   n={len(lag2)} median {statistics.median(lag2):.2f}h  <2h {sum(1 for x in lag2 if x<2)/len(lag2)*100:.0f}%")
for m,v in sorted(lagm.items(),key=lambda kv:-len(kv[1])):
    print(f"   {m:5} n={len(v):4d} median {statistics.median(v):6.2f}h  <2h {sum(1 for x in v if x<2)/len(v)*100:4.0f}%")
print("no board quote in 72h window:",dict(mk))
