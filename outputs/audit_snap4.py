import csv, os, sys, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
snapg=set(r["game_id"] for r in csv.DictReader(open(os.path.join(R,"live_snapshots.csv"),encoding="utf-8")))
p=os.path.join(R,"elo_model","plays_full.csv")
hdr=open(p,encoding="utf-8").readline().strip().split(",")
print("plays_full columns:",hdr[:12])
col=[c for c in hdr if "game" in c.lower()][0]
pg=set()
for r in csv.DictReader(open(p,encoding="utf-8")): pg.add(r[col])
print("plays_full games:",len(pg))
print("OVERLAP with 27 snapshot games:",len(pg & snapg), sorted(pg & snapg)[:5])
print("sample plays_full ids:",sorted(pg)[:3]," sample snap ids:",sorted(snapg)[:3])
print("\n=== SURVIVORSHIP: which games got in-play capture? ===")
g=list(csv.DictReader(open(os.path.join(R,"data","games_2026.csv"),encoding="utf-8")))
print("total 2026 games in box:",len(g)," with live in-play odds+state:",len(snapg),
      "= %.1f%%"%(100*len(snapg)/len(g)))
dates=sorted(x["date"] for x in g if x["game_id"] in snapg)
print("captured-game date span:",dates[0],"->",dates[-1],"| distinct dates:",len(set(dates)))
alld=sorted(set(x["date"] for x in g))
print("full season date span:",alld[0],"->",alld[-1])
