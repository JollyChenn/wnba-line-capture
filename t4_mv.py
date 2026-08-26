import os, sys, collections, statistics
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, D)
from t4_lib import base
R = base()
SIGS = ("flip", "hotover", "overshoot"); BM = ("pra", "pr", "pts")
cand = [r for r in R if any(s in SIGS for s in r["srcs"]) and r["mk"] in BM and r["prev"] is not None]
c = collections.Counter(round(r["line"]-r["prev"], 2) for r in cand)
print("line move (tonight - previous game), signal candidates n=%d" % len(cand))
tot = 0
for k in sorted(c):
    won = sum(1 for r in cand if abs((r["line"]-r["prev"])-k) < 1e-6 and r["actual"] > r["line"])
    nn = c[k]; tot += nn
    pay = sum((r["over"]-1) if r["actual"] > r["line"] else -1.0
              for r in cand if abs((r["line"]-r["prev"])-k) < 1e-6)
    print("   mv %+5.1f  n=%-4d  over-win %.0f%%  ROI %+7.1f%%" % (k, nn, 100*won/nn, 100*pay/nn))
print("  total", tot)
print("")
# same on the WHOLE board (mechanism check, law 6): does a non-raised line predict an over anywhere?
allr = [r for r in R if r["prev"] is not None]
print("FULL BOARD mechanism check, n=%d, %d games" % (len(allr), len(set(r["gt"] for r in allr))))
buck = collections.defaultdict(list)
for r in allr:
    mv = r["line"]-r["prev"]
    b = "cut <=-1" if mv <= -1 else ("cut -0.5" if mv < 0 else ("flat 0" if mv == 0 else ("+0.5" if mv <= 0.5 else "raised >=1")))
    buck[b].append(r)
for b in ("cut <=-1", "cut -0.5", "flat 0", "+0.5", "raised >=1"):
    v = buck[b]
    if not v: continue
    w = sum(1 for r in v if r["actual"] > r["line"])
    roi = sum((r["over"]-1) if r["actual"] > r["line"] else -1.0 for r in v)/len(v)
    # raw production: actual minus line, in units of her own sd
    z = statistics.mean((r["actual"]-r["line"])/max(r["sd"] or 1, 1) for r in v if r["sd"])
    print("   %-11s n=%-5d over-win %.1f%%  overROI %+6.1f%%  mean (actual-line)/sd %+.3f" % (
        b, len(v), 100*w/len(v), 100*roi, z))
