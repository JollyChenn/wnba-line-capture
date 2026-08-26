import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
bi = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t,o,ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None: bi[((b.get("player") or "").lower(), b.get("market"), b.get("side"), ln)].append((t,o))
R=list(csv.DictReader(open(os.path.join(D,"fam_bets.csv"),encoding="utf-8")))
c=[x for x in R if x["src"]=="cascade" and not x["oppod"]]
h=[]
for x in c:
    gt=ts(x["gt"]); T=ts(x["T"])
    opp="Under" if x["sd"]=="Over" else "Over"
    v=bi.get((x["pl"],x["mk"],opp,float(x["ln"])))
    if not v: h.append(("none",None)); continue
    dts=[(t-gt).total_seconds()/3600 for t,_ in v]
    h.append(("some", (min(dts),max(dts))))
print(collections.Counter(k for k,_ in h))
ex=[v for k,v in h if k=="some"][:15]
print("hours rel to tip (min,max):", [(round(a,1),round(b,1)) for a,b in ex])
allmin=[v[0] for k,v in h if k=="some"]
print("median earliest opp quote hrs before tip:", round(statistics.median(allmin),1))
# also T rel to gt for all cascade
print("cascade T-gt hrs:", statistics.median([(ts(x["T"])-ts(x["gt"])).total_seconds()/3600 for x in R if x["src"]=="cascade"]))
print("all bets T-gt hrs by src:")
for s in sorted(set(x["src"] for x in R)):
    a=[(ts(x["T"])-ts(x["gt"])).total_seconds()/3600 for x in R if x["src"]==s]
    print(f"  {s:<11} median {statistics.median(a):+.1f}h")
