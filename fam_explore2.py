import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])

G = load("graded_bets.csv"); L = load("bets_log.csv")
def nd(s): return (s or "").replace("-","")[:8]
def key(r): return (nd(r["date"]), (r["player"] or "").lower(), r["market"], r["side"], float(r["line"]))
lg = collections.defaultdict(list)
for r in L: lg[key(r)].append(r)
hit=0; tiers=0
for r in G:
    k=key(r)
    if k in lg: hit+=1
print("join hit", hit, "of", len(G))
# check tier agreement + ev availability
n_ev=0
for r in G[:5]:
    k=key(r); print(r["src"], r["tier"], [ (x["captured_utc"],x["tier"],x["ev"],x["src"],x["odds"]) for x in lg.get(k,[])][:3])

# why no_board_side for 206
dt2tip = collections.defaultdict(list)
for (pl,tp),row in pgrow.items(): dt2tip[(pl,row["date"])].append(tp)
miss=collections.Counter(); mkmiss=collections.Counter()
for r in G:
    pl=(r["player"] or "").lower(); d=nd(r["date"])
    tps=dt2tip.get((pl,d))
    if not tps: continue
    gt=tps[0]
    if (pl,r["market"],gt) not in side:
        miss[r["src"]]+=1; mkmiss[r["market"]]+=1
print("no board side by src", dict(miss)); print("by market", dict(mkmiss))
print("markets in graded", collections.Counter(x["market"] for x in G))
