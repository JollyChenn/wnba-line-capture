# time_dim.py - go deeper in the ONE dimension that has ever worked.
# ---------------------------------------------------------------------------------------------
# Today's structural finding: 1xbet's prop LINES match Pinnacle's (64% exactly, median gap 0.0).
# The 7% softness is loaded into the PRICE, not the number. So there is no lazy number to take
# by looking sideways at another book - and that is why every cross-book and cross-market test
# this week came back empty.
#
# What the star does instead is compare 1xbet TO ITSELF ACROSS GAMES. It is a TIME-dimension
# filter, and it is the only thing that works. The star uses the crudest possible version of that
# idea: one lag, binary, "did the number rise since her last game". This tests the richer versions
# that follow from the same mechanism:
#
#   HOLD STREAK    how many consecutive games has this number NOT moved? A number that has sat
#                  still for four games while her production changed is staler than one that just
#                  held once.
#   TWO-GAME LAG   the number versus two games ago, not one - catches a slow drift the star misses
#                  because each single step was under the threshold.
#   TEAM DIVERGENCE the book moved her TEAMMATES' numbers this game but not hers. That is
#                  inattention aimed specifically at her, which is the cleanest possible reading
#                  of the thesis.
#   FORM GAP       her recent production versus the number that has not moved - staleness only
#                  pays if reality has actually changed underneath it.
#
# Pre-registered grid, global permutation over the whole thing. Same discipline as everything else.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260831)
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

MKTS = ("pra", "pr", "pts")
SIGS = ("flip", "hotover", "overshoot")
gm = {g.get("game_id"): (g.get("date", ""), ts(g.get("tip"))) for g in load("data/games_2026.csv")}
plog = collections.defaultdict(list); team = {}
for r in load("data/box_2026.csv"):
    dt, tp = gm.get(r.get("game_id"), ("", None))
    if not dt or tp is None: continue
    p_, rb, a = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    pl = (r.get("player") or "").lower()
    plog[pl].append(dict(tip=tp, date=dt, pts=p_, pra=p_+rb+a, pr=p_+rb))
    team[pl] = r.get("team")
for v in plog.values(): v.sort(key=lambda x: x["tip"])
tips_of = collections.defaultdict(list)
for g in load("data/games_2026.csv"):
    t = ts(g.get("tip"))
    if t: tips_of[g["home"]].append(t); tips_of[g["away"]].append(t)
for v in tips_of.values(): v.sort()
def game_for(tm, when):
    for t in tips_of.get(tm, []):
        if when <= t and (t-when).total_seconds() <= 60*3600: return t
    return None

raw = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None and b.get("market") in MKTS and b.get("side") == "Over":
        raw[((b.get("player") or "").lower(), b.get("market"), ln)].append((t, o))
bygame = collections.defaultdict(list)
for (pl, mk, ln), v in raw.items():
    tm = team.get(pl)
    if not tm: continue
    for t, o in sorted(v):
        g2 = game_for(tm, t)
        if g2: bygame[(pl, mk, g2)].append((t, ln, o))
for v in bygame.values(): v.sort()

# her full line history per market, in game order - the raw material for every time feature
lines_of = collections.defaultdict(list)
for (pl, mk, gt), seq in bygame.items():
    lines_of[(pl, mk)].append((gt, seq[-1][1], seq[-1][2]))
for v in lines_of.values(): v.sort()

# every team's set of moved/held lines per game, for the divergence feature
team_moves = collections.defaultdict(lambda: [0, 0])
for (pl, mk), v in lines_of.items():
    tm = team.get(pl)
    if not tm: continue
    for i in range(1, len(v)):
        gt, ln, _ = v[i]; prev = v[i-1][1]
        team_moves[(tm, gt)][0] += 1
        if abs(ln - prev) >= 0.5: team_moves[(tm, gt)][1] += 1

seen, K = set(), []
for b in sorted(load("bets_log.csv"), key=lambda r: r.get("captured_utc") or ""):
    if b.get("side") != "Over" or b.get("src") not in SIGS: continue
    pl, mk = (b.get("player") or "").lower(), b.get("market")
    if mk not in MKTS: continue
    t0, tm = ts(b.get("captured_utc")), team.get(pl)
    if not (t0 and tm): continue
    gt = game_for(tm, t0)
    if not gt or (pl, mk, gt) in seen: continue
    hist = lines_of.get((pl, mk), [])
    idx = next((i for i, x in enumerate(hist) if x[0] == gt), None)
    if idx is None or idx < 1: continue
    rec = next((g for g in plog.get(pl, []) if g["tip"] == gt), None)
    if not rec: continue
    seen.add((pl, mk, gt))
    line, price = hist[idx][1], hist[idx][2]
    if rec[mk] == line: continue
    prev1 = hist[idx-1][1]
    if line - prev1 >= 0.5: continue                       # MODEL S: starred only
    # HOLD STREAK - consecutive prior games with the identical number
    streak = 0
    for j in range(idx-1, -1, -1):
        if abs(hist[j][1] - line) < 0.01: streak += 1
        else: break
    prev2 = hist[idx-2][1] if idx >= 2 else None
    # FORM GAP - her last 3 games in this market versus the number that has not moved
    prior = [g[mk] for g in plog.get(pl, []) if g["tip"] < gt]
    form3 = statistics.mean(prior[-3:]) if len(prior) >= 3 else None
    mv, held = team_moves.get((tm, gt), [0, 0])
    K.append(dict(pl=pl, mk=mk, date=rec["date"], gt=gt, odds=price, won=rec[mk] > line, line=line,
                  streak=streak,
                  lag2=(None if prev2 is None else line - prev2),
                  formgap=(None if form3 is None else form3 - line),
                  tm_moved=held, tm_total=mv,
                  tm_share=(held/mv if mv >= 3 else None)))
byday = collections.defaultdict(list)
for r in K: byday[r["date"]].append(r)
for dd in list(byday):
    best = {}
    for r in sorted(byday[dd], key=lambda x: -x["odds"]): best.setdefault(r["pl"], r)
    byday[dd] = list(best.values())
K = [r for v in byday.values() for r in v]
print(f"{len(K)} starred Model S bets with a full line history")
for lbl, key in (("hold streak", "streak"), ("two-game lag", "lag2"),
                 ("form gap", "formgap"), ("teammate move share", "tm_share")):
    print(f"    {lbl:<22} {sum(1 for r in K if r.get(key) is not None):>4} of {len(K)}")
print("")

def roi(rows): return sum((r["odds"]-1) if r["won"] else -1.0 for r in rows)/len(rows) if rows else 0.0
def show(rows, label, minn=15):
    n = len(rows)
    if n < minn:
        print(f"  {label:<44} n={n:<4} too few"); return
    w = sum(1 for r in rows if r["won"])
    print(f"  {label:<44} n={n:<4} {100*w/n:5.1f}%  ROI {100*roi(rows):+6.1f}%")

CELLS = []
def reg(name, sel):
    g = [r for r in K if sel(r)]
    if len(g) >= 15: CELLS.append((name, sel))
    show(g, f"  {name}")

print("="*104)
print("  1. HOLD STREAK - consecutive games this number has NOT moved")
print("="*104)
for s in (1, 2, 3):
    reg(f"streak == {s}", lambda r, s=s: r["streak"] == s)
reg("streak >= 3", lambda r: r["streak"] >= 3)
reg("streak >= 4", lambda r: r["streak"] >= 4)
print("")
print("="*104)
print("  2. TWO-GAME LAG - the number versus TWO games ago")
print("="*104)
reg("fell over 2 games", lambda r: r["lag2"] is not None and r["lag2"] < 0)
reg("flat over 2 games", lambda r: r["lag2"] is not None and r["lag2"] == 0)
reg("rose over 2 games (star missed it)", lambda r: r["lag2"] is not None and r["lag2"] > 0)
print("")
print("="*104)
print("  3. FORM GAP - her last 3 games versus the unmoved number")
print("="*104)
fg = sorted(r["formgap"] for r in K if r["formgap"] is not None)
if fg:
    med = fg[len(fg)//2]
    print(f"  median form gap {med:+.2f}  (positive = she has been beating the number)")
    reg("form ABOVE the line (median+)", lambda r, m=med: r["formgap"] is not None and r["formgap"] >= m)
    reg("form BELOW the line", lambda r, m=med: r["formgap"] is not None and r["formgap"] < m)
    reg("form 3+ above the line", lambda r: r["formgap"] is not None and r["formgap"] >= 3)
print("")
print("="*104)
print("  4. TEAM DIVERGENCE - the book moved her teammates' numbers but not hers")
print("="*104)
reg("book moved NO teammate line", lambda r: r["tm_share"] is not None and r["tm_share"] == 0)
reg("book moved SOME teammate lines", lambda r: r["tm_share"] is not None and 0 < r["tm_share"] < 0.5)
reg("book moved MOST teammate lines", lambda r: r["tm_share"] is not None and r["tm_share"] >= 0.5)
print("")
print("="*104)
print(f"  GLOBAL PERMUTATION over all {len(CELLS)} pre-registered cells")
print("="*104)
def best_of(lab):
    b = -9e9; bl = ""
    for nm, sel in CELLS:
        g = [r for r in K if sel(r)]
        if len(g) < 15: continue
        v = sum((r["odds"]-1) if lab[id(r)] else -1.0 for r in g)/len(g)
        if v > b: b, bl = v, nm
    return b, bl
real, rlbl = best_of({id(r): r["won"] for r in K})
outs = [r["won"] for r in K]
T = 3000; beat = 0; sims = []
for _ in range(T):
    sh = outs[:]; random.shuffle(sh)
    v, _ = best_of({id(r): w for r, w in zip(K, sh)})
    sims.append(v)
    if v >= real: beat += 1
sims.sort()
print(f"  baseline (all {len(K)} bets): ROI {100*roi(K):+.1f}%")
print(f"  BEST CELL: {rlbl}  ROI {100*real:+.1f}%")
print(f"  shuffled best-of-grid: median {100*sims[T//2]:+.1f}%  p95 {100*sims[int(T*0.95)]:+.1f}%")
print(f"  GLOBAL p = {beat/T:.4f}")
