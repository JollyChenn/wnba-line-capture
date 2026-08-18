# mate_pattern.py - when MODEL S PASSES on a player, is there a pattern in her TEAMMATES?
# ---------------------------------------------------------------------------------------------
# Not the earlier question. That one conditioned on our pick HITTING, which is unknowable at bet
# time and therefore unbettable. This conditions only on the PASS - the moment the live model
# fires - which is known hours before tip.
#
# The story to test: Model S fires when the book has left a scorer's number alone. If the book is
# inattentive to that GAME rather than to that PLAYER, the inattention should show up on her
# teammates' numbers too, and we would have several bets a night instead of one.
#
# Every interval here is a PLAYER-BLOCK bootstrap. The rank re-audit showed why: 1,466 quotes
# collapsed to 58 players, and the quote-level interval was roughly three times too tight. Prop
# quotes cluster by player and by game, and a null that ignores that manufactures significance.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260917)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])

BET_MKTS = ("pra", "pr", "pts"); SIGS = ("flip", "hotover", "overshoot")
# ---- reconstruct every MODEL S PASS, exactly as the live card defines one -----------------------
# src in SIGS, market in BET_MKTS, and the book did NOT raise her 0.5+ since her previous game.
# `starred` on the board rows already encodes that test against the same prevline table.
passes = set()                       # (player, gametip)
pass_games = set()                   # (team, gametip)
for r in B:
    if r["mk"] in BET_MKTS and r.get("starred") is True:
        passes.add((r["pl"], r["gt"])); pass_games.add((r["tm"], r["gt"]))
print(f"{len(B)} board quotes | {len(passes)} model-S-shaped player-games on {len(pass_games)} team-games")
print("")

def roi(rows, w):
    if not rows: return 0.0
    if w == "over":
        return 100*sum((r["over_od"]-1) if r["over_won"] else -1.0 for r in rows)/len(rows)
    return 100*sum((r["under_od"]-1) if not r["over_won"] else -1.0 for r in rows)/len(rows)
def hit(rows, w):
    if not rows: return 0.0
    return 100*sum(1 for r in rows if (r["over_won"] if w == "over" else not r["over_won"]))/len(rows)
def boot(rows, w, T=2000):
    """resample PLAYERS with replacement - quotes inside a player move together"""
    bp = collections.defaultdict(list)
    for r in rows: bp[r["pl"]].append(r)
    keys = list(bp)
    if len(keys) < 8: return None, None
    out = []
    for _ in range(T):
        pick = [random.choice(keys) for _ in keys]
        out.append(roi([r for p in pick for r in bp[p]], w))
    out.sort()
    return out[int(T*.025)], out[int(T*.975)]
def show(rows, label, w="over", minn=80):
    n = len(rows)
    if n < minn:
        print(f"  {label:<44} n={n:<5} too few"); return
    lo, hi = boot(rows, w)
    npl = len({r["pl"] for r in rows})
    ci = f"[{lo:+5.1f}%,{hi:+6.1f}%]" if lo is not None else "     -        "
    print(f"  {label:<44} n={n:<5} {npl:>3}pl  {hit(rows,w):5.1f}%  ROI {roi(rows,w):+6.1f}%  95CI {ci}")

# a teammate quote = same team, same game, different player, on a game where S passed
MATE, BASE = [], []
for r in B:
    if (r["tm"], r["gt"]) in pass_games and (r["pl"], r["gt"]) not in passes:
        MATE.append(r)
    elif (r["tm"], r["gt"]) not in pass_games:
        BASE.append(r)
print("="*112)
print("  1. THE HEADLINE - do teammates of a Model S pass behave differently at all?")
print("="*112)
for w in ("over", "under"):
    print(f"  --- {w.upper()} ---")
    show(BASE, "  quotes on NON-pass team-games (baseline)", w)
    show(MATE, "  TEAMMATE of a Model S pass", w)
    show([r for r in B if (r["pl"], r["gt"]) in passes], "  the pass herself (reference)", w)
    print("")
print("="*112)
print("  2. BY TEAMMATE ROLE - who absorbs it?")
print("="*112)
for w in ("over", "under"):
    print(f"  --- teammate {w.upper()} ---")
    for k in range(1, 6):
        show([r for r in MATE if r["rank"] == k], f"    teammate rank {k}", w, minn=60)
    print("")
print("="*112)
print("  3. BY MARKET - does the inattention travel to a particular stat?")
print("="*112)
for w in ("over", "under"):
    print(f"  --- teammate {w.upper()} ---")
    for mk in ALL_MK:
        show([r for r in MATE if r["mk"] == mk], f"    teammate {mk}", w, minn=60)
    print("")
print("="*112)
print("  4. IS THE TEAMMATE ALSO UNRAISED? (the game-level inattention story)")
print("="*112)
print("  if the book ignored the whole GAME, the teammate whose number was ALSO left alone is")
print("  where it should show. if it ignored only the player, this split does nothing.")
print("")
for w in ("over", "under"):
    print(f"  --- teammate {w.upper()} ---")
    show([r for r in MATE if r.get("starred") is True],  "    teammate ALSO unraised", w, minn=60)
    show([r for r in MATE if r.get("starred") is False], "    teammate WAS raised", w, minn=60)
    show([r for r in BASE if r.get("starred") is True],  "    unraised on a non-pass game (ctrl)", w, minn=60)
    print("")
print("="*112)
print("  5. HOW MANY PASSES ON THE SAME TEAM-GAME? (does stacking mean anything)")
print("="*112)
cnt = collections.Counter(tm_gt for tm_gt in (( p[0] and None) for p in []))
per = collections.Counter()
for pl, gt in passes:
    tm = next((r["tm"] for r in B if r["pl"] == pl and r["gt"] == gt), None)
    if tm: per[(tm, gt)] += 1
dist = collections.Counter(per.values())
print("  passes per team-game: " + ", ".join(f"{k}:{v}" for k, v in sorted(dist.items())))
for w in ("over",):
    for c in (1, 2, 3):
        rows = [r for r in B if (r["pl"], r["gt"]) in passes and per.get((r["tm"], r["gt"]), 0) == c]
        show(rows, f"    pass on a team-game with {c} pass(es)", w, minn=60)
print("")
print("="*112)
print("  6. PERMUTATION - shuffle which TEAM-GAMES were passes, keeping game blocks intact")
print("="*112)
print("  the label being tested is at the team-game level, so that is the level to shuffle at.")
print("")
tg_all = sorted({(r["tm"], r["gt"]) for r in B})
bytg = collections.defaultdict(list)
for r in B: bytg[(r["tm"], r["gt"])].append(r)
npass = len(pass_games)
GRID = [("mate over", "over", lambda r: True), ("mate under", "under", lambda r: True)]
for k in range(1, 5):
    GRID.append((f"mate rank{k} over", "over", lambda r, k=k: r["rank"] == k))
    GRID.append((f"mate rank{k} under", "under", lambda r, k=k: r["rank"] == k))
def best(pg):
    bb, bl = -9e9, ""
    for nm, w, sel in GRID:
        rows = [r for tg in pg for r in bytg[tg] if sel(r)]
        if len(rows) < 120: continue
        v = roi(rows, w)
        if v > bb: bb, bl = v, nm
    return bb, bl
real, rlbl = best(pass_games)
T = 2000; beat = 0; sims = []
for _ in range(T):
    pg = set(random.sample(tg_all, npass))
    v, _ = best(pg)
    sims.append(v)
    if v >= real: beat += 1
sims.sort()
print(f"  real best: {rlbl}  {real:+.1f}%")
print(f"  shuffled best-of-grid: median {sims[T//2]:+.1f}%  p95 {sims[int(T*.95)]:+.1f}%  max {sims[-1]:+.1f}%")
print(f"  BLOCK p = {beat/T:.4f}")
