import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])

print("board rows", len(B))
print("markets", collections.Counter(r["mk"] for r in B))
print("date range", min(r["date"] for r in B), max(r["date"] for r in B))

H = load("data/halves_2026.csv")
print("halves rows", len(H), H[0] if H else None)
hg = set(r["game_id"] for r in H)
print("halves games", len(hg), "in gmeta", len(hg & set(gmeta)))
# date range of halves
hd = sorted(set(r["date"] for r in H))
print("halves date range", hd[0], hd[-1], "n dates", len(hd))

P = load("elo_model/plays_full.csv")
print("plays rows", len(P))
pg = set(r["game_id"] for r in P)
print("plays games", len(pg), "in gmeta", len(pg & set(gmeta)))
pgd = sorted(set(gmeta[g][0] for g in pg if g in gmeta))
print("plays game dates", pgd[0] if pgd else None, pgd[-1] if pgd else None, len(pgd))
print("periods", collections.Counter(r["period"] for r in P).most_common(8))
