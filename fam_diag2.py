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
n_other=0; n_none=0; diffs=[]
for x in c[:2000]:
    pl,mk,ln=x["pl"],x["mk"],float(x["ln"])
    opp = "Under" if x["sd"]=="Over" else "Over"
    lines=[k[3] for k in bi if k[0]==pl and k[1]==mk and k[2]==opp]
    if lines:
        n_other+=1; diffs.append(min(abs(l-ln) for l in lines))
    else: n_none+=1
print("cascade missing-opp: opp side exists at other lines for",n_other,"; no opp side at all",n_none)
print("median line distance to nearest opp line", statistics.median(diffs) if diffs else None)
# does the Over side exist at that line? (i.e. is the bet's own line on the board at all)
own=0
for x in c[:2000]:
    if (x["pl"],x["mk"],x["sd"],float(x["ln"])) in bi: own+=1
print("own side present on board:", own, "of", len(c))
# capture-time of cascade bets rel to tip
L=load("bets_log.csv")
cl=[r for r in L if r["src"]=="cascade"]
print("cascade log rows", len(cl), "sample", cl[0] if cl else None)
