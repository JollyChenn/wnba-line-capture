# under_and_role.py - three questions at once, all on the FULL board so there is real power.
# ---------------------------------------------------------------------------------------------
#   1 ROLE: does any of this depend on whether she is the team's top scorer or a role player?
#   2 FADE: assist overs hit 47.3% - is the UNDER side of these markets the actual bet?
#   3 pa   : specifically, is the under better in pa, which we do not currently trade?
#
# Both sides are priced from the board's own Over AND Under quotes at the same line, so no
# side is scored at "1 minus the other price" - that mistake fakes an edge every time.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260911)
D = os.path.dirname(os.path.abspath(__file__))

def load(p):
    fp = os.path.join(D, p)
    return list(csv.DictReader(open(fp, encoding="utf-8", errors="replace"))) if os.path.exists(fp) else []
def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except Exception: return None

ALL_MK = ("pts", "pra", "pr", "pa", "reb", "ast", "ra")
gmeta = {}
for g in load("data/games_2026.csv"):
    t = ts(g.get("tip"))
    if t: gmeta[g.get("game_id")] = (g.get("date", ""), t)
pgrow = {}; roster = collections.defaultdict(set); teamof = {}
for r in load("data/box_2026.csv"):
    gid = r.get("game_id")
    if gid not in gmeta: continue
    dt, tp = gmeta[gid]
    pl, tm = (r.get("player") or "").lower(), r.get("team")
    p_, rb, a = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    pgrow[(pl, tp)] = dict(tm=tm, tip=tp, date=dt, min=f(r.get("min")) or 0,
                           pts=p_, reb=rb, ast=a, pra=p_+rb+a, pr=p_+rb, pa=p_+a, ra=rb+a)
    roster[(tm, tp)].add(pl); teamof[pl] = tm
hist = collections.defaultdict(list)
for (pl, tp), row in pgrow.items(): hist[pl].append(row)
for v in hist.values(): v.sort(key=lambda x: x["tip"])
tips_of = collections.defaultdict(list)
for g in load("data/games_2026.csv"):
    t = ts(g.get("tip"))
    if t: tips_of[g["home"]].append(t); tips_of[g["away"]].append(t)
for v in tips_of.values(): v.sort()
def game_for(tm, when):
    for t in tips_of.get(tm, []):
        if when <= t and (t-when).total_seconds() <= 60*3600: return t
    return None

# BOTH sides, same line, latest quote each
raw = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None and b.get("market") in ALL_MK:
        raw[((b.get("player") or "").lower(), b.get("market"), b.get("side"), ln)].append((t, o))
side = collections.defaultdict(dict)
for (pl, mk, sd, ln), v in raw.items():
    tm = teamof.get(pl)
    if not tm: continue
    for t, o in sorted(v):
        g2 = game_for(tm, t)
        if not g2: continue
        cur = side[(pl, mk, g2)].get(sd)
        if cur is None or t > cur[0]: side[(pl, mk, g2)][sd] = (t, ln, o)

B = []
for (pl, mk, gt), sd in side.items():
    if "Over" not in sd or "Under" not in sd: continue
    if sd["Over"][1] != sd["Under"][1]: continue        # only compare at the SAME line
    now = pgrow.get((pl, gt))
    if not now or now["min"] < 8: continue
    line = sd["Over"][1]
    if now[mk] == line: continue
    prior = [x for x in hist.get(pl, []) if x["tip"] < gt][-6:]
    if len(prior) < 4: continue
    # role: her scoring rank inside the team, from games BEFORE this one
    mates = {}
    for m in roster.get((now["tm"], gt), ()):
        pv = [x for x in hist.get(m, []) if x["tip"] < gt][-6:]
        if pv: mates[m] = statistics.mean(x["pts"] for x in pv)
    rank = (sorted(mates, key=lambda m: -mates[m]).index(pl) + 1) if pl in mates else 99
    B.append(dict(pl=pl, mk=mk, gt=gt, line=line, over_od=sd["Over"][2], under_od=sd["Under"][2],
                  over_won=now[mk] > line, rank=rank))
print(f"{len(B)} player-market-games with BOTH sides quoted at the same line")
print("")

def cell(rows, which):
    n = len(rows)
    if not n: return None
    if which == "over":
        w = sum(1 for r in rows if r["over_won"])
        u = sum((r["over_od"]-1) if r["over_won"] else -1.0 for r in rows)
        be = 100/(sum(r["over_od"] for r in rows)/n)
    else:
        w = sum(1 for r in rows if not r["over_won"])
        u = sum((r["under_od"]-1) if not r["over_won"] else -1.0 for r in rows)
        be = 100/(sum(r["under_od"] for r in rows)/n)
    return n, 100*w/n, 100*u/n, be

print("="*104)
print("  1. EVERY MARKET, BOTH SIDES - is the UNDER the bet anywhere?")
print("="*104)
print(f"  {'market':<7}{'n':>6}{'OVER hit':>11}{'OVER roi':>11}{'be':>7}   {'UNDER hit':>11}{'UNDER roi':>11}{'be':>7}")
for mk in ALL_MK:
    g = [r for r in B if r["mk"] == mk]
    if len(g) < 60:
        print(f"  {mk:<7}{len(g):>6}   too few"); continue
    o = cell(g, "over"); u = cell(g, "under")
    print(f"  {mk:<7}{o[0]:>6}{o[1]:>10.1f}%{o[2]:>+10.1f}%{o[3]:>7.1f}   "
          f"{u[1]:>10.1f}%{u[2]:>+10.1f}%{u[3]:>7.1f}")
print("")
print("="*104)
print("  2. BY ROLE - top scorer vs role player (scoring rank on her own team)")
print("="*104)
print(f"  {'role':<22}{'n':>6}{'OVER roi':>11}{'UNDER roi':>12}")
for lo, hi, lbl in ((1, 1, "TOP scorer (rank 1)"), (2, 2, "second option"),
                    (3, 4, "rank 3-4"), (5, 99, "role player (5+)")):
    g = [r for r in B if lo <= r["rank"] <= hi]
    if len(g) < 60:
        print(f"  {lbl:<22}{len(g):>6}   too few"); continue
    o = cell(g, "over"); u = cell(g, "under")
    print(f"  {lbl:<22}{o[0]:>6}{o[2]:>+10.1f}%{u[2]:>+11.1f}%")
print("")
print("  and the same split inside pa and ast specifically:")
for mk in ("pa", "ast"):
    print(f"    --- {mk} ---")
    for lo, hi, lbl in ((1, 2, "top 2 scorers"), (3, 99, "everyone else")):
        g = [r for r in B if r["mk"] == mk and lo <= r["rank"] <= hi]
        if len(g) < 40:
            print(f"      {lbl:<20}{len(g):>5}  too few"); continue
        o = cell(g, "over"); u = cell(g, "under")
        print(f"      {lbl:<20}{o[0]:>5}  over {o[2]:+6.1f}%   under {u[2]:+6.1f}%  (be {u[3]:.1f})")
print("")
print("="*104)
print("  3. GLOBAL PERMUTATION over every cell above")
print("="*104)
CELLS = []
for mk in ALL_MK:
    for w in ("over", "under"):
        CELLS.append((f"{mk} {w}", lambda r, m=mk: r["mk"] == m, w))
for lo, hi, lbl in ((1,1,"rank1"), (2,2,"rank2"), (3,4,"rank34"), (5,99,"rank5+")):
    for w in ("over", "under"):
        CELLS.append((f"{lbl} {w}", lambda r, a=lo, b_=hi: a <= r["rank"] <= b_, w))
def best(lab):
    bb = -9e9; bl = ""
    for nm, sel, w in CELLS:
        g = [r for r in B if sel(r)]
        if len(g) < 60: continue
        if w == "over":
            v = sum((r["over_od"]-1) if lab[id(r)] else -1.0 for r in g)/len(g)
        else:
            v = sum((r["under_od"]-1) if not lab[id(r)] else -1.0 for r in g)/len(g)
        if v > bb: bb, bl = v, nm
    return bb, bl
real, rlbl = best({id(r): r["over_won"] for r in B})
outs = [r["over_won"] for r in B]
T = 2000; beat = 0
for _ in range(T):
    random.shuffle(outs)
    v, _ = best({id(r): w for r, w in zip(B, outs)})
    if v >= real: beat += 1
print(f"  {len(CELLS)} cells tested.  best: {rlbl}  ROI {100*real:+.1f}%")
print(f"  GLOBAL p = {beat/T:.4f}")
