# verify_fixes.py - confirm both data-layer fixes landed and quantify what they changed.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
print("FIX 1 - name resolution")
print(f"  unresolved board names remaining: {len(_UNRESOLVED)}  ({sum(_UNRESOLVED.values())} rows)")
for k, v in _UNRESOLVED.most_common(5): print(f"     {k} ({v})")
w = [k for k in teamof if "wilson" in k]
print(f"  A'ja Wilson now in teamof? {[k for k in w if 'ja wilson' in k or 'aja' in k]}")
gradable = 0
for (pl, mk, gt), sdq in side.items():
    if "Over" in sdq and "Under" in sdq and abs(sdq["Over"][1]-sdq["Under"][1]) < 0.01:
        now = pgrow.get((pl, gt))
        if now and mk in now and now[mk] != sdq["Over"][1]: gradable += 1
print(f"  gradable two-sided quotes now: {gradable}")
print()
print("FIX 2 - main-line extraction")
tots = [v["tot"][1] for v in GM.values() if "tot" in v]
skews = [v["tot"][2] for v in GM.values() if "tot" in v]
print(f"  games with a total: {len(tots)}   median total {statistics.median(tots):.1f}")
print(f"  median |price skew| of chosen rung: {statistics.median(skews):.4f}  (main line -> near 0)")
print(f"  rungs with skew > 0.05 (i.e. still an alternate): {sum(1 for x in skews if x > 0.05)}")
