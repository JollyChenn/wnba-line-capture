import os, sys, json, collections, statistics
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, D)
from t4_lib import base
R = base()
S = [r for r in R if r["sharp"] is not None]
print("rows with a sharp line read at tip-6h (<=10h stale): %d / %d" % (len(S), len(R)))
print("   games %d  players %d" % (len(set(r["gt"] for r in S)), len(set(r["pl"] for r in S))))
print("   by month:", collections.Counter(r["date"][:6] for r in S).most_common())
print("   by market:", collections.Counter(r["mk"] for r in S).most_common())
print("   with a signal src:", sum(1 for r in S if r["srcs"]))
g = [round(r["sharp"] - r["line"], 2) for r in S]
print("   gap distribution: |gap|>=0.5 %d  >=1 %d  >=1.5 %d  >=2 %d" % (
    sum(1 for x in g if abs(x) >= .5), sum(1 for x in g if abs(x) >= 1),
    sum(1 for x in g if abs(x) >= 1.5), sum(1 for x in g if abs(x) >= 2)))
print("   mean gap %+.3f  median %+.2f" % (statistics.mean(g), statistics.median(g)))
# where does the sharp line come from
import csv
pb = list(csv.DictReader(open(os.path.join(D, "pinn_board.csv"), encoding="utf-8", errors="replace")))
print("pinn_board.csv rows %d  dates %s .. %s" % (len(pb), min(r["date"] for r in pb), max(r["date"] for r in pb)))
bl = list(csv.DictReader(open(os.path.join(D, "bets_log.csv"), encoding="utf-8", errors="replace")))
withp = [r for r in bl if (r.get("pinn") or "").strip()]
print("bets_log rows with a pinn line %d  dates %s .. %s" % (
    len(withp), min(r["date"] for r in withp), max(r["date"] for r in withp)))
print("   bets_log pinn coverage by month:", collections.Counter(r["date"][:7] for r in withp).most_common())
