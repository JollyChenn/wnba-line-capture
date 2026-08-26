import os, sys, csv, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hlib; ROOT = hlib.boot(globals())
random.seed(20260826)

H = load("data/halves_2026.csv")
print("halves rows", len(H))
names = set((r["player"] or "").strip().lower() for r in H)
boxnames = set(teamof)
print("halves distinct players", len(names), "in box:", len(names & boxnames), "missing:", len(names-boxnames))
print("sample missing:", sorted(names-boxnames)[:15])
gids = set(r["game_id"] for r in H)
print("halves games", len(gids), "in gmeta:", len(gids & set(gmeta)))
ds = sorted(set(r["date"] for r in H))
print("date range", ds[0], ds[-1], "n dates", len(ds))
bd = sorted(set(gt for (pl,mk,gt) in side if mk=="pts"))
print("board pts game-tips", len(bd), bd[0].date(), bd[-1].date())
bad = sum(1 for r in H if f(r["h1_pts"])+f(r["h2_pts"]) != f(r["pts"]))
print("h1+h2 != pts rows:", bad)
ok=0; miss=0; dis=0
for r in H:
    gid=r["game_id"]
    if gid not in gmeta: miss+=1; continue
    tp=gmeta[gid][1]; k=(r["player"].strip().lower(), tp)
    if k in pgrow:
        ok+=1
        if pgrow[k]["pts"]!=f(r["pts"]): dis+=1
    else: miss+=1
print("halves->pgrow join ok", ok, "miss", miss, "pts disagree", dis)
