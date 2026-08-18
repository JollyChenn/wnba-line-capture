# streak_probe.py - the one new cell that cleared a 74-cell noise ceiling. Break it.
# ---------------------------------------------------------------------------------------------
# "over-streak 2" = she went over HER OWN POSTED LINE in each of her last two games. Backing the
# over again returned +4.4% on n=543, above the +4.2% p95 ceiling of the whole grid.
#
# It is worth more than rank 4 for two reasons. It was not cherry-picked - rank 4 came out of an
# earlier script today, so its place in that grid was already contaminated, while this cell was
# tested for the first time. And it points the right way: streak 1 is -2.2%, streak 2 is +4.4%,
# so the effect grows with the streak instead of spiking at one arbitrary value.
#
# The obvious confound is that the book RAISES her line after two overs, which would make this
# the star filter wearing a different hat. That is test 4 and it is the one that matters.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260915)
D = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
exec(src.split('print(f"{len(B)} two-sided board quotes')[0])

def cell(rows, which="over"):
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
def show(rows, label, which="over", minn=60):
    n, h, r_, be = cell(rows, which)
    if n < minn:
        print(f"  {label:<46} n={n:<5} too few"); return
    print(f"  {label:<46} n={n:<5} {h:5.1f}%  ROI {r_:+6.1f}%  be {be:.1f}%  cushion {h-be:+.1f}pp")

print(f"{len(B)} quotes")
dts = sorted({r['date'] for r in B}); cut = dts[int(len(dts)*0.6)]
print("")
print("="*106)
print("  1. IS IT MONOTONIC? (streak = consecutive games she beat her own posted line)")
print("="*106)
for s in range(0, 4):
    g = [r for r in B if r["streak"] == s]
    show(g, f"  streak {s}  OVER", "over", minn=40)
print("")
print("  and the mirror - if the over rises with the streak, the under must fall:")
for s in range(0, 4):
    show([r for r in B if r["streak"] == s], f"  streak {s}  UNDER", "under", minn=40)
print("")
print("="*106)
print("  2. OUT OF SAMPLE  (split " + cut + ")")
print("="*106)
for s in (0, 1, 2):
    g = [r for r in B if r["streak"] == s]
    show([r for r in g if r["date"] <  cut], f"  streak {s}  IN ", "over", minn=40)
    show([r for r in g if r["date"] >= cut], f"  streak {s}  OUT", "over", minn=40)
    print("")
print("="*106)
print("  3. BY MARKET - carried by one, or broad?")
print("="*106)
s2 = [r for r in B if r["streak"] >= 2]
for mk in ALL_MK:
    show([r for r in s2 if r["mk"] == mk], f"  streak2+ {mk}", "over", minn=40)
print("")
print("="*106)
print("  4. THE CONFOUND - is this just the star filter again?")
print("="*106)
print("  after two overs the book usually RAISES her. If the streak cell is really the star cell,")
print("  it should die once we hold the star fixed.")
print("")
for lbl, sel in (("STARRED (line not raised)", lambda r: r.get("starred") is True),
                 ("RAISED (line went up 0.5+)", lambda r: r.get("starred") is False)):
    print(f"  --- {lbl} ---")
    for s in (0, 1, 2):
        show([r for r in B if sel(r) and r["streak"] == s], f"    streak {s}", "over", minn=40)
    print("")
n_st = sum(1 for r in B if r["streak"] >= 2 and r.get("starred") is True)
n_ra = sum(1 for r in B if r["streak"] >= 2 and r.get("starred") is False)
print(f"  of {len(s2)} streak-2+ quotes: {n_st} starred, {n_ra} raised "
      f"({100*n_ra/max(1,n_st+n_ra):.0f}% raised - if this were ~100% the two would be inseparable)")
print("")
print("="*106)
print("  5. DOES IT STACK WITH THE OTHER LEADS?")
print("="*106)
show([r for r in B if r["streak"] >= 2 and r["rank"] == 2], "  streak2+ AND rank2", "over", minn=40)
show([r for r in B if r["streak"] >= 2 and r["rank"] != 2], "  streak2+ NOT rank2", "over", minn=40)
show([r for r in B if r["streak"] < 2 and r["rank"] == 2], "  rank2 WITHOUT streak", "over", minn=40)
print("")
show([r for r in B if r["streak"] >= 2 and r.get("starred") is True],
     "  streak2+ AND starred (the stack)", "over", minn=40)
print("")
print("="*106)
print("  6. IS IT JUST 'SHE IS IN FORM'? (form = her 5-game mean minus the line)")
print("="*106)
fm = sorted(r["form"] for r in B); med = fm[len(fm)//2]
for lbl, sel in (("form ABOVE median", lambda r: r["form"] >= med),
                 ("form BELOW median", lambda r: r["form"] < med)):
    print(f"  --- {lbl} ---")
    for s in (0, 1, 2):
        show([r for r in B if sel(r) and r["streak"] == s], f"    streak {s}", "over", minn=40)
    print("")
print("="*106)
print("  7. DEDICATED PERMUTATION on the streak family alone (8 cells)")
print("="*106)
CELLS = [(f"streak{s} {w}", s, w) for s in range(4) for w in ("over", "under")]
def best(lab):
    bb, bl = -9e9, ""
    for nm, s, w in CELLS:
        g = [r for r in B if r["streak"] == s]
        if len(g) < 120: continue
        v = (sum((r["over_od"]-1) if lab[id(r)] else -1.0 for r in g)/len(g) if w == "over"
             else sum((r["under_od"]-1) if not lab[id(r)] else -1.0 for r in g)/len(g))
        if v > bb: bb, bl = v, nm
    return bb, bl
real, rlbl = best({id(r): r["over_won"] for r in B})
outs = [r["over_won"] for r in B]; T = 3000; beat = 0
for _ in range(T):
    random.shuffle(outs)
    v, _ = best({id(r): w for r, w in zip(B, outs)})
    if v >= real: beat += 1
print(f"  best: {rlbl}  ROI {100*real:+.1f}%   family p = {beat/T:.4f}")
print("")
print("  (the family p is generous - it prices only these 8 cells. the honest number is the")
print("   74-cell global p=0.0207 from mega_sweep, and even that ignores the scripts run before it.)")
