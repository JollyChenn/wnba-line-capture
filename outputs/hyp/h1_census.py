import os, sys, csv, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hlib; ROOT = hlib.boot(globals())
random.seed(20260826)

H1 = {}
for r in load("outputs/hyp/h1_all.csv"):
    gid = r["game_id"]
    if gid not in gmeta: continue
    H1[(r["player"], gmeta[gid][1])] = dict(h1=f(r["h1"]), h2=f(r["h2"]), pts=f(r["pts"]), src=r["src"], date=r["date"])
print("H1 keyed player-games (in gmeta):", len(H1))
bd = sorted(set(x["date"] for x in pgrow.values()))
print("box date range", bd[0], bd[-1], "player-games", len(pgrow))

# two-sided pts quotes with a same-game H1
Q = {}
for (pl, mk, gt), sd in side.items():
    if mk != "pts" or "Over" not in sd or "Under" not in sd: continue
    if sd["Over"][1] != sd["Under"][1]: continue
    Q[(pl, gt)] = dict(line=sd["Over"][1], oo=sd["Over"][2], uo=sd["Under"][2],
                       ot=sd["Over"][0], ut=sd["Under"][0])
print("two-sided pts quotes (matched lines):", len(Q))
G = [(pl, gt) for (pl, gt) in Q if (pl, gt) in H1 and pgrow.get((pl, gt))]
print("...with H1 AND box for the same game (candidate G):", len(G))
dts = sorted(set(gt.date() for pl, gt in G)); print("  G window", dts[0], dts[-1], "game-days", len(dts))

ev = 0; ev_l = collections.Counter()
for pl, gt in G:
    h = H1[(pl, gt)]; q = Q[(pl, gt)]
    if h["h1"] > q["line"]: ev += 1
print(f"EVENT h1 > posted line: {ev} / {len(G)} = {ev/len(G):.2%}")
# by minutes filter
G8 = [(p,g) for p,g in G if pgrow[(p,g)]["min"] >= 8]
ev8 = sum(1 for p,g in G8 if H1[(p,g)]["h1"] > Q[(p,g)]["line"])
print(f"  min>=8 subset: {ev8}/{len(G8)} = {ev8/len(G8):.2%}")
# also full-game clear rate for reference
fg = sum(1 for p,g in G if pgrow[(p,g)]["pts"] > Q[(p,g)]["line"])
print(f"  (full-game over rate on same set: {fg}/{len(G)} = {fg/len(G):.2%})")

# pairs: G -> her next game with a two-sided quote
def nxt(pl, gt):
    c = sorted(g for (p, g) in Q if p == pl and g > gt)
    return c[0] if c else None
pairs = []
for pl, gt in G:
    n = nxt(pl, gt)
    if n and pgrow.get((pl, n)): pairs.append((pl, gt, n))
print("G -> G+1 pairs with a bettable next quote:", len(pairs))
print("  distinct players", len(set(p for p,_,_ in pairs)), "distinct G+1 games", len(set(gmeta_lookup:=[n for _,_,n in pairs])))
ep = sum(1 for p,g,n in pairs if H1[(p,g)]["h1"] > Q[(p,g)]["line"])
print(f"  of which EVENT (cleared by half in G): {ep}")
gap = [ (n-g).days for p,g,n in pairs ]
print("  days between G and G+1: median %.1f  p90 %.1f  max %d" % (statistics.median(gap), sorted(gap)[int(.9*len(gap))], max(gap)))
