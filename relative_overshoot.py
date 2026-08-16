# relative_overshoot.py - why reb/ast/ra never fire, and whether a relative threshold fixes it.
# ---------------------------------------------------------------------------------------------
# THE MECHANICAL REASON. overshoot_overs() fires when the book's line sits 3+ BELOW her trailing
# median. That is an ABSOLUTE threshold applied to markets of wildly different size:
#     PRA line 30  ->  3 points is a 10% gap
#     REB line 5.5 ->  3 boards is a 55% gap
# So a rebound line essentially never qualifies, which is why the engine has emitted 46 reb,
# 23 ast and 5 ra signals all season against 890 for pr - even though 1xbet quotes rebounds for
# 111 players. The market is there; the threshold locks us out of it.
#
# This rebuilds the signal from the BOARD directly, market-agnostic, using a RELATIVE gap, and
# grades it. Everything is reconstructed from data we already hold, so every market gets the
# same treatment and the comparison is fair.
#
# It is a NEW signal invented after looking at the data, so it gets the same discipline as
# everything else: pre-registered grid, out-of-sample split, and a global permutation test over
# the whole grid rather than a p-value on the winner.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260824)
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

ALL = ("pts", "pra", "pr", "pa", "reb", "ast", "ra")
gm = {g.get("game_id"): (g.get("date", ""), ts(g.get("tip"))) for g in load("data/games_2026.csv")}
plog = collections.defaultdict(list); team = {}
for r in load("data/box_2026.csv"):
    dt, tp = gm.get(r.get("game_id"), ("", None))
    if not dt or tp is None: continue
    p_, rb, a = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    pl = (r.get("player") or "").lower()
    plog[pl].append(dict(tip=tp, date=dt, pts=p_, reb=rb, ast=a,
                         pra=p_+rb+a, pr=p_+rb, pa=p_+a, ra=rb+a))
    team[pl] = r.get("team")
for v in plog.values(): v.sort(key=lambda x: x["tip"])

tips_of = collections.defaultdict(list)
for g in load("data/games_2026.csv"):
    t = ts(g.get("tip"))
    if t: tips_of[g["home"]].append(t); tips_of[g["away"]].append(t)
for v in tips_of.values(): v.sort()
def game_for(tm, when):
    for t in tips_of.get(tm, []):
        if when <= t and (t - when).total_seconds() <= 60*3600: return t
    return None

raw = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None and b.get("market") in ALL and b.get("side") == "Over":
        raw[((b.get("player") or "").lower(), b.get("market"), ln)].append((t, o))
bygame = collections.defaultdict(list)
for (pl, mk, ln), v in raw.items():
    tm = team.get(pl)
    if not tm: continue
    for t, o in sorted(v):
        g2 = game_for(tm, t)
        if g2: bygame[(pl, mk, g2)].append((t, ln, o))
for v in bygame.values(): v.sort()

# ---- one row per (player, market, game) straight off the board --------------------------------
C = []
for (pl, mk, gt), seq in bygame.items():
    rec = next((g for g in plog.get(pl, []) if g["tip"] == gt), None)
    if not rec: continue
    prior = [g[mk] for g in plog.get(pl, []) if g["tip"] < gt][-10:]
    if len(prior) < 6: continue                       # need a real median
    med = statistics.median(prior)
    if med <= 0: continue
    line, price = seq[-1][1], seq[-1][2]
    if rec[mk] == line: continue                      # push
    earlier = sorted(g for (p2, m2, g) in bygame if p2 == pl and m2 == mk and g < gt)
    pv = bygame[(pl, mk, earlier[-1])][-1][1] if earlier else None
    C.append(dict(pl=pl, mk=mk, gt=gt, date=rec["date"], line=line, odds=price, med=med,
                  gap_abs=med - line, gap_rel=(med - line)/med,
                  won=rec[mk] > line,
                  star=(pv is not None and line - pv < 0.5), noprev=(pv is None)))
print(f"{len(C)} player-market-games reconstructed straight from the board")
by = collections.Counter(r["mk"] for r in C)
print("  by market: " + ", ".join(f"{k} {v}" for k, v in sorted(by.items())))
print("")
print("="*104)
print("  THE LOCKOUT, MEASURED: what a 3-point absolute gap means in each market")
print("="*104)
print(f"  {'market':<8}{'median line':>13}{'3pts as % of median':>22}{'rows with gap_abs>=3':>23}")
for mk in ALL:
    g = [r for r in C if r["mk"] == mk]
    if not g: continue
    ml = statistics.median([r["med"] for r in g])
    n3 = sum(1 for r in g if r["gap_abs"] >= 3)
    print(f"  {mk:<8}{ml:>13.1f}{100*3/ml:>21.0f}%{n3:>16} / {len(g)}")
print("")
print("  That is the lockout: 3 points is a tenth of a PRA line and more than half a rebound line.")
print("")

def roi(rows): return sum((r["odds"]-1) if r["won"] else -1.0 for r in rows)/len(rows) if rows else 0.0
def show(rows, label, minn=25):
    n = len(rows)
    if n < minn:
        print(f"  {label:<40} n={n:<5} too few"); return
    w = sum(1 for r in rows if r["won"])
    print(f"  {label:<40} n={n:<5} {100*w/n:5.1f}%  ROI {100*roi(rows):+6.1f}%")

# ---- PRE-REGISTERED GRID: markets x relative-gap thresholds, star required ---------------------
THRESH = (0.10, 0.15, 0.20, 0.25, 0.30)
GROUPS = [("small (reb/ast/ra)", ("reb","ast","ra")), ("pa", ("pa",)),
          ("live markets (pra/pr/pts)", ("pra","pr","pts")), ("ALL markets", ALL)]
print("="*104)
print("  RELATIVE-GAP SIGNAL, STARRED ONLY - pre-registered grid")
print("="*104)
cells = []
for glbl, mks in GROUPS:
    print(f"  --- {glbl} ---")
    for th in THRESH:
        g = [r for r in C if r["mk"] in mks and r["star"] and not r["noprev"] and r["gap_rel"] >= th]
        show(g, f"    gap >= {100*th:.0f}% of median")
        if len(g) >= 25: cells.append((f"{glbl} gap>={100*th:.0f}%", g))
    print("")
if not cells:
    print("  no cell reached n=25 - nothing to test"); raise SystemExit
best_lbl, best_g = max(cells, key=lambda c: roi(c[1]))
print("="*104)
print(f"  BEST CELL: {best_lbl}  n={len(best_g)}  ROI {100*roi(best_g):+.1f}%")
print("="*104)
dates = sorted({r["date"] for r in C}); cut = dates[int(len(dates)*0.6)]
show([r for r in best_g if r["date"] <  cut], "  IN sample", minn=10)
show([r for r in best_g if r["date"] >= cut], "  OUT of sample", minn=10)
print("")
print("  GLOBAL PERMUTATION over the whole grid (outcomes shuffled, 1000 runs):")
outs = [r["won"] for r in C]
real = roi(best_g)
beat = 0; T = 1000
for _ in range(T):
    sh = outs[:]; random.shuffle(sh)
    lab = {id(r): w for r, w in zip(C, sh)}
    b = -9e9
    for glbl, mks in GROUPS:
        for th in THRESH:
            g = [r for r in C if r["mk"] in mks and r["star"] and not r["noprev"] and r["gap_rel"] >= th]
            if len(g) < 25: continue
            v = sum((r["odds"]-1) if lab[id(r)] else -1.0 for r in g)/len(g)
            b = max(b, v)
    if b >= real: beat += 1
print(f"    shuffled best-of-grid beat ours {beat}/{T}  ->  GLOBAL p = {beat/T:.4f}")
