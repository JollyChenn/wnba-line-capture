# PART A3 - ROSTER TURNOVER.  Is turnover derivable from box data across seasons?  Yes: box_full.csv
# covers 2019-2026.  Proxy = share of LAST season's team minutes played by players who have suited
# up for the SAME team in the current season's first 3 games (strictly pre-game for games >=4).
import os, sys, csv, math, statistics, collections, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
from tk_lib import load_games, annotate, ROOT, block_boot
random.seed(20260826)

G = annotate(load_games())
REAL = collections.defaultdict(set)
for g in G: REAL[g["season"]].add(g["home"]); REAL[g["season"]].add(g["away"])

GF = {r["game_id"]: r for r in csv.DictReader(open(os.path.join(ROOT,"elo_model","games_full.csv"), encoding="utf-8"))}
BX = list(csv.DictReader(open(os.path.join(ROOT,"elo_model","box_full.csv"), encoding="utf-8")))

# team-season minutes last year
lastmin = collections.defaultdict(float)      # (season,team,player) -> minutes
teammin = collections.defaultdict(float)      # (season,team) -> minutes
# ordered team-season game list to identify first 3 games
tgames = collections.defaultdict(list)
for gid, r in GF.items():
    s = int(r["season"])
    for t in (r["home"], r["away"]):
        if t in REAL.get(s, ()):
            tgames[(s,t)].append((r["date"], gid))
for k in tgames: tgames[k].sort()
first3 = {k: set(gid for _, gid in v[:3]) for k, v in tgames.items()}

for b in BX:
    g = GF.get(b["game_id"])
    if not g: continue
    s = int(g["season"]); t = b["team"]
    if t not in REAL.get(s, ()): continue
    try: m = float(b["min"] or 0)
    except Exception: m = 0.0
    lastmin[(s,t,b["player"])] += m
    teammin[(s,t)] += m

roster3 = collections.defaultdict(set)
for b in BX:
    g = GF.get(b["game_id"])
    if not g: continue
    s = int(g["season"]); t = b["team"]
    if b["game_id"] in first3.get((s,t), ()):
        try: m = float(b["min"] or 0)
        except Exception: m = 0.0
        if m > 0: roster3[(s,t)].add(b["player"])

RET = {}
for (s,t), tot in teammin.items():
    if s-1 not in REAL or t not in REAL.get(s-1, ()) or teammin.get((s-1,t),0) <= 0:
        continue
    prev_tot = teammin[(s-1,t)]
    back = sum(m for (ss,tt,p), m in lastmin.items() if ss==s-1 and tt==t and p in roster3.get((s,t), ()))
    RET[(s,t)] = back / prev_tot
print("returning-minutes share computable for", len(RET), "team-seasons (2020-2026; 2019 has no prior season in box_full)")
vals = sorted(RET.values())
print("  distribution: min %.3f  p25 %.3f  med %.3f  p75 %.3f  max %.3f" % (vals[0], vals[len(vals)//4], statistics.median(vals), vals[3*len(vals)//4], vals[-1]))
for s in sorted(set(k[0] for k in RET)):
    v = [RET[k] for k in RET if k[0]==s]
    print(f"   {s}: n={len(v)} mean returning share={statistics.mean(v):.3f}")

lo_c = vals[len(vals)//3]; hi_c = vals[2*len(vals)//3]
def tb(x): return "T_hi_turnover" if x < lo_c else ("T_mid" if x < hi_c else "T_lo_turnover")
TORD = ["T_hi_turnover","T_mid","T_lo_turnover"]
print(f"  tercile cuts on returning share: <{lo_c:.3f} = HIGH turnover, >{hi_c:.3f} = LOW turnover")

# window: current-season games 4..15 (early, and strictly after the 3-game roster read)
def elig(g, side):
    i = g["tgi_h"] if side=="h" else g["tgi_a"]
    t = g["home"] if side=="h" else g["away"]
    return 4 <= i <= 15 and (g["season"], t) in RET

# ---- MECHANISM FIRST: is the spread error larger for high-turnover teams early? ----
print("\n=== MECHANISM: signed spread error from the eligible team's perspective, by turnover tercile ===")
mech = collections.defaultdict(list); mechabs = collections.defaultdict(list)
for g in G:
    if g["spread"] is None: continue
    for side in ("h","a"):
        if not elig(g, side): continue
        t = g["home"] if side=="h" else g["away"]
        sgn = 1 if side=="h" else -1
        mech[tb(RET[(g["season"],t)])].append(sgn*(g["margin"] + g["spread"]))
        mechabs[tb(RET[(g["season"],t)])].append(abs(g["margin"] + g["spread"]))
for b in TORD:
    v = mech.get(b, [])
    if not v: continue
    se = statistics.pstdev(v)/math.sqrt(len(v))
    print(f"  {b:16s} n={len(v):4d}  signed cover margin={statistics.mean(v):+6.2f} (t={statistics.mean(v)/se:+5.2f})   |spread err|={statistics.mean(mechabs[b]):6.2f}")

# ---- DECLARED GRID: 3 terciles x 2 side bets (ML_side, SP_side) = 6 cells; min n = 60 ----
MINN = 60
print("\nDECLARED GRID A3: 3 turnover terciles x 2 side-bets = 6 cells, window = team games 4-15, min n = %d" % MINN)

def build(labmap):
    cells = collections.defaultdict(list)
    for g in G:
        for side in ("h","a"):
            if not elig(g, side): continue
            t = g["home"] if side=="h" else g["away"]
            b = labmap[(g["season"], t)]
            if g["ml_h"] and g["ml_a"]:
                w = (1.0 if g["margin"]>0 else 0.0) if side=="h" else (1.0 if g["margin"]<0 else 0.0)
                o = g["ml_h"] if side=="h" else g["ml_a"]
                cells[(b,"ML_side")].append((o-1.0) if w else -1.0)
            if g["spread"] is not None and g["sp_h"] and g["sp_a"]:
                d = (g["margin"]+g["spread"]) * (1 if side=="h" else -1)
                if d == 0: continue
                o = g["sp_h"] if side=="h" else g["sp_a"]
                cells[(b,"SP_side")].append((o-1.0) if d>0 else -1.0)
    return cells

real_map = {k: tb(v) for k, v in RET.items()}
# ceiling: permute tercile labels across TEAM-SEASONS within season (label lives at team-season level)
rnd = random.Random(99)
bests = []
for _ in range(2000):
    pm = {}
    for s in sorted(set(k[0] for k in RET)):
        ks = [k for k in RET if k[0]==s]
        labs = [real_map[k] for k in ks]; rnd.shuffle(labs)
        for k, l in zip(ks, labs): pm[k] = l
    c = build(pm)
    b = max((sum(v)/len(v) for v in c.values() if len(v)>=MINN), default=-9)
    bests.append(b)
bests.sort()
CEIL = bests[int(0.95*len(bests))]
print(f"NOISE CEILING (2000 team-season-level permutations, best of 6 cells): p95 = {CEIL*100:+.2f}%\n")

c = build(real_map)
print(f"{'tercile':16s} {'ML_side':>24s} {'SP_side':>24s}")
for b in TORD:
    line = f"{b:16s}"
    for bt in ("ML_side","SP_side"):
        v = c.get((b,bt), [])
        line += f" {(sum(v)/len(v)*100 if v else 0):+8.2f}% n={len(v):<4d}   " if v else f"{'--':>24s}"
    print(line)
best = max(((sum(v)/len(v), k, len(v)) for k, v in c.items() if len(v)>=MINN), default=(None,None,0))
print(f"\nBEST: {best[1]} ROI={best[0]*100:+.2f}% n={best[2]}  vs ceiling {CEIL*100:+.2f}% -> {'CLEARS' if best[0]>CEIL else 'UNDER CEILING (noise)'}")
