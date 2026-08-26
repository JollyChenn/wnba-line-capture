import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])

G = load("graded_bets.csv")
L = load("bets_log.csv")
print("graded", len(G), "log", len(L))
print("log src:", collections.Counter(x["src"] for x in L).most_common())
print("log tier:", collections.Counter(x["tier"] for x in L).most_common())

# join key
def key(r): return (r["date"], (r["player"] or "").lower(), r["market"], r["side"], r["line"])
lg = collections.defaultdict(list)
for r in L: lg[key(r)].append(r)
hit=0; multi=0
for r in G:
    k=key(r)
    if k in lg:
        hit+=1
        if len(set(x["captured_utc"] for x in lg[k]))>1: multi+=1
print("graded rows with log match:", hit, "of", len(G), " multi-capture:", multi)

# map graded -> game tip
# player date -> tip
dt2tip = collections.defaultdict(list)
for (pl,tp),row in pgrow.items():
    dt2tip[(pl,row["date"].replace("-",""))].append(tp)
gt_hit=0; side_hit=0; both_hit=0
miss=collections.Counter()
for r in G:
    pl=(r["player"] or "").lower(); d=r["date"]
    tps=dt2tip.get((pl,d)) or dt2tip.get((pl,d[:4]+"-"+d[4:6]+"-"+d[6:]))
    if not tps: miss["no_box"]+=1; continue
    gt_hit+=1
    gt=tps[0]
    sd=side.get((pl,r["market"],gt))
    if not sd: miss["no_board_side"]+=1; continue
    side_hit+=1
    if "Over" in sd and "Under" in sd: both_hit+=1
    else: miss["one_sided"]+=1
print("gt resolved",gt_hit,"board side",side_hit,"two-sided",both_hit, dict(miss))
print("sample dates in box:", list(pgrow.values())[0]["date"])
