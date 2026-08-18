# fade_low_rank.py - the low ranks lose badly on the over. Is the UNDER the bet there?
# ---------------------------------------------------------------------------------------------
# rank 4's over returns -18.4% at a 43.2% hit rate. Its under therefore hits 56.8%, against a
# break-even near 53% - so on the face of it the fade should pay. The earlier table pooled ranks
# 3 and 4 and showed -2.9%, which would have hidden it: rank 3's over is 51.0%, so ITS under is
# a loser, and pooling a good cell with a bad one averages the finding away.
#
# Every fade below is priced from the board's own UNDER quote at the same line. Four fades this
# week have landed within a point of zero because the book's cut is paid twice, so the bar is
# whether any rank clears its own under break-even by a real margin.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260913)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "under_and_role.py"), encoding="utf-8").read().split('print(f"{len(B)} player-market-games')[0])
for r in B: r["date"] = pgrow[(r["pl"], r["gt"])]["date"]

def cell(rows, which):
    n = len(rows)
    if not n: return 0, 0, 0, 0
    if which == "over":
        w = sum(1 for r in rows if r["over_won"])
        u = sum((r["over_od"]-1) if r["over_won"] else -1.0 for r in rows)
        be = 100/(sum(r["over_od"] for r in rows)/n)
    else:
        w = sum(1 for r in rows if not r["over_won"])
        u = sum((r["under_od"]-1) if not r["over_won"] else -1.0 for r in rows)
        be = 100/(sum(r["under_od"] for r in rows)/n)
    return n, 100*w/n, 100*u/n, be

print(f"{len(B)} two-sided quotes")
print("")
print("="*104)
print("  BOTH SIDES, RANK BY RANK - unpooled, because pooling 3 with 4 hid this")
print("="*104)
print(f"  {'rank':<8}{'n':>6}{'OVER hit':>11}{'OVER roi':>11}   {'UNDER hit':>11}{'UNDER roi':>11}{'u-be':>8}{'cushion':>10}")
for k in range(1, 8):
    g = [r for r in B if r["rank"] == k]
    if len(g) < 100:
        print(f"  {k:<8}{len(g):>6}   too few"); continue
    o = cell(g, "over"); u = cell(g, "under")
    print(f"  {k:<8}{o[0]:>6}{o[1]:>10.1f}%{o[2]:>+10.1f}%   {u[1]:>10.1f}%{u[2]:>+10.1f}%{u[3]:>7.1f}%"
          f"{u[1]-u[3]:>+9.1f}pp")
print("")
print("  cushion = under hit rate minus its own break-even. Positive means the fade pays.")
print("")
print("="*104)
print("  THE LOW-RANK FADE, GROUPED THE WAY YOU WOULD ACTUALLY BET IT")
print("="*104)
def show(rows, label, which, minn=80):
    n, h, r_, be = cell(rows, which)
    if n < minn:
        print(f"  {label:<40} n={n:<5} too few"); return
    print(f"  {label:<40} n={n:<5} {h:5.1f}%  ROI {r_:+6.1f}%  be {be:.1f}%  cushion {h-be:+.1f}pp")
show([r for r in B if r["rank"] >= 4], "fade rank 4+ (under)", "under")
show([r for r in B if r["rank"] >= 5], "fade rank 5+ (under)", "under")
show([r for r in B if r["rank"] == 4], "fade rank 4 only", "under")
show([r for r in B if r["rank"] <= 2], "fade rank 1-2 (control, should lose)", "under")
print("")
print("="*104)
print("  OUT OF SAMPLE")
print("="*104)
dts = sorted({r["date"] for r in B}); cut = dts[int(len(dts)*0.6)]
print(f"  split {cut}")
for lbl, sel in (("fade rank 4+", lambda r: r["rank"] >= 4),
                 ("fade rank 4 only", lambda r: r["rank"] == 4),
                 ("rank2 over (the other lead)", None)):
    if sel is None:
        g = [r for r in B if r["rank"] == 2]
        show([r for r in g if r["date"] < cut], f"  {lbl}  IN", "over", minn=50)
        show([r for r in g if r["date"] >= cut], f"  {lbl}  OUT", "over", minn=50)
        continue
    g = [r for r in B if sel(r)]
    show([r for r in g if r["date"] < cut], f"  {lbl}  IN", "under", minn=50)
    show([r for r in g if r["date"] >= cut], f"  {lbl}  OUT", "under", minn=50)
print("")
print("="*104)
print("  BY MARKET - where does the low-rank fade actually live?")
print("="*104)
lo = [r for r in B if r["rank"] >= 4]
for mk in ALL_MK:
    show([r for r in lo if r["mk"] == mk], f"  rank4+ {mk} under", "under", minn=60)
print("")
print("="*104)
print("  GLOBAL PERMUTATION - every rank x side cell, 14 in total")
print("="*104)
CELLS = []
for k in range(1, 8):
    for w in ("over", "under"):
        CELLS.append((f"rank{k} {w}", k, w))
def best(lab):
    bb = -9e9; bl = ""
    for nm, k, w in CELLS:
        g = [r for r in B if r["rank"] == k]
        if len(g) < 100: continue
        if w == "over":
            v = sum((r["over_od"]-1) if lab[id(r)] else -1.0 for r in g)/len(g)
        else:
            v = sum((r["under_od"]-1) if not lab[id(r)] else -1.0 for r in g)/len(g)
        if v > bb: bb, bl = v, nm
    return bb, bl
real, rlbl = best({id(r): r["over_won"] for r in B})
outs = [r["over_won"] for r in B]
T = 3000; beat = 0
for _ in range(T):
    random.shuffle(outs)
    v, _ = best({id(r): w for r, w in zip(B, outs)})
    if v >= real: beat += 1
print(f"  best of {len(CELLS)} cells: {rlbl}  ROI {100*real:+.1f}%   GLOBAL p = {beat/T:.4f}")
