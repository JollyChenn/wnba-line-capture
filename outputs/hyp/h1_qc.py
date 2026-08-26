import os, sys, csv, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hlib; ROOT = hlib.boot(globals())
A = load("outputs/hyp/h1_all.csv")
d = collections.Counter(); big = []
for r in A:
    gid = r["game_id"]
    if gid not in gmeta: continue
    tp = gmeta[gid][1]; row = pgrow.get((r["player"], tp))
    if not row: continue
    diff = f(r["pts"]) - row["pts"]
    d[diff] += 1
    if abs(diff) >= 2 and r["src"] == "pbp": big.append((r["player"], r["date"], f(r["pts"]), row["pts"]))
print("pbp/halves total minus box total distribution:", sorted(d.items())[:12], "...", sorted(d.items())[-6:])
tot = sum(d.values()); print("n", tot, "exact", d[0]/tot, "|d|<=1", sum(v for k,v in d.items() if abs(k)<=1)/tot)
print("sample large diffs:", big[:8])
# per source
for src in ("halves","pbp"):
    dd=[]
    for r in A:
        if r["src"]!=src: continue
        gid=r["game_id"]
        if gid not in gmeta: continue
        row=pgrow.get((r["player"], gmeta[gid][1]))
        if row: dd.append(f(r["pts"])-row["pts"])
    if dd: print(src, "n",len(dd),"exact %.3f"%(sum(1 for x in dd if x==0)/len(dd)), "mean %.3f"%statistics.mean(dd))
