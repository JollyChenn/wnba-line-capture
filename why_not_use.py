# why_not_use.py - "there are tons of positive-ROI cells, why not use them?"
# ---------------------------------------------------------------------------------------------
# The best question asked all week, and the answer is not obvious. Every cell in that sweep is
# positive because MODEL S ITSELF is positive: +12.1% across all 99 bets. Slicing a profitable
# model produces profitable slices. The question is never "is this cell positive" - it is "is
# this cell better than the model I already have, by more than chance produces".
#
# So this takes the REAL 99 bets and invents filters that CANNOT possibly work - random coin
# flips, a player's name length, whether the date is odd - and reports their ROI. If a meaningless
# filter routinely produces +20-30% cells, then a +20% cell is not evidence of anything.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260902)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "time_dim.py"), encoding="utf-8").read().split('def roi(rows):')[0])

def roi(rows): return sum((r["odds"]-1) if r["won"] else -1.0 for r in rows)/len(rows) if rows else 0.0
BASE = roi(K)
print("=" * 100)
print(f"  THE MODEL ITSELF: {len(K)} bets, ROI {100*BASE:+.1f}%")
print("=" * 100)
print("")
print("  Now here are FOUR FILTERS THAT CANNOT POSSIBLY WORK, applied to those same bets:")
print("")
fakes = [
    ("player's surname starts A-M", lambda r: r["pl"].split()[-1][0] <= "m"),
    ("date is an odd number",       lambda r: int(r["date"]) % 2 == 1),
    ("line has a .5 in the tens",   lambda r: int(r["line"]) % 2 == 0),
    ("coin flip (seeded)",          lambda r: random.Random(hash(r["pl"]) & 0xffff).random() < 0.5),
]
print(f"  {'nonsense filter':<34}{'kept':>6}{'ROI':>9}   {'dropped':>8}{'ROI':>9}")
for lbl, sel in fakes:
    a = [r for r in K if sel(r)]; b = [r for r in K if not sel(r)]
    if len(a) < 10 or len(b) < 10: continue
    print(f"  {lbl:<34}{len(a):>6}{100*roi(a):>+8.1f}%   {len(b):>8}{100*roi(b):>+8.1f}%")
print("")
print("  Every one of those splits is meaningless by construction, and several look as good as")
print("  the 'real' cells from the sweep.")
print("")
print("=" * 100)
print("  THE DISTRIBUTION - 5000 RANDOM 50/50 splits of the same 99 bets")
print("=" * 100)
hi, lo, gaps = [], [], []
for _ in range(5000):
    idx = list(range(len(K))); random.shuffle(idx)
    a = [K[i] for i in idx[:len(K)//2]]; b = [K[i] for i in idx[len(K)//2:]]
    ra, rb = roi(a), roi(b)
    hi.append(max(ra, rb)); lo.append(min(ra, rb)); gaps.append(abs(ra-rb))
hi.sort(); lo.sort(); gaps.sort()
print(f"  the BETTER half of a random split:  median {100*hi[2500]:+.1f}%   p90 {100*hi[4500]:+.1f}%"
      f"   p99 {100*hi[4950]:+.1f}%")
print(f"  the WORSE half:                     median {100*lo[2500]:+.1f}%   p10 {100*lo[500]:+.1f}%")
print(f"  the GAP between the two halves:     median {100*gaps[2500]:.1f}pp  p90 {100*gaps[4500]:.1f}pp"
      f"  p99 {100*gaps[4950]:.1f}pp")
print("")
print("  So splitting these 99 bets at random typically hands you one half at "
      f"{100*hi[2500]:+.0f}% and the other at {100*lo[2500]:+.0f}%,")
print(f"  a {100*gaps[2500]:.0f}pp gap, from nothing at all. The sweep's real gaps were 20-39pp.")
print("")
print("=" * 100)
print("  AND THE BIGGEST CELL IS NOT A FILTER AT ALL")
print("=" * 100)
big = [r for r in K if r["tm_share"] is not None and r["tm_share"] >= 0.5]
print(f"  'book moved MOST teammate lines' keeps {len(big)} of {len(K)} bets = "
      f"{100*len(big)/len(K):.0f}% of the model.")
print(f"  ROI {100*roi(big):+.1f}% against the model's own {100*BASE:+.1f}%.")
print("  A filter that keeps 78% of your bets and moves ROI by 9pp has not found anything -")
print("  it has mostly just relabelled the model, and the 22 bets it drops are the tail.")
print("")
print("=" * 100)
print("  WHAT WOULD ACTUALLY CONVINCE ME")
print("=" * 100)
print("  1. the gap survives a GLOBAL permutation over every cell tested   (ours: p=0.891)")
print("  2. it holds in BOTH time halves at similar size                   (ours: collapses)")
print("  3. it is monotonic in an ordered variable, not good-bad-good      (ours: not)")
print("  4. it has a mechanism you would have predicted BEFOREHAND          (only the star does)")
print("  5. it still works on bets it was not derived from                  (untested at n=99)")
print("")
print("  The star clears all five. Nothing found this week clears more than two.")
