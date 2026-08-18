# tier_test.py - should gate 5 be a FILTER (bet/skip) or a TIER (bet more/less)?
# ------------------------------------------------------------------------------------------
# A tier is only defensible if the underlying variable is MONOTONIC. This project already has a
# scar from ignoring that: S_paper's confidence tiers ran THIN +34.8%, SOLID -13.9%, STRONG
# +19.5% - good, bad, good across an ORDERED variable - and that non-monotonicity is why it was
# kept on paper. So before staking 2u on anything, check that more of the good thing is better.
import csv, os, sys, random, collections, statistics
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260926)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "gate5.py"), encoding="utf-8").read()
     .split('print(f"{len(A)} bets with gates 1+2 on')[0])
S = [r for r in A if r["star"] == "starred"]          # OLD MODEL S, judged at the ping line
def sc(rows):
    n = len(rows); w = sum(1 for r in rows if r["won"])
    u = sum((r["od"]-1) if r["won"] else -1.0 for r in rows)
    return n, 100*w/n, u, 100*u/n
def pb(rows, T=3000):
    bp = collections.defaultdict(list)
    for r in rows: bp[r["pl"]].append(r)
    k = list(bp); o = []
    for _ in range(T):
        g = [x for p in [random.choice(k) for _ in k] for x in bp[p]]
        o.append(100*sum((x["od"]-1) if x["won"] else -1.0 for x in g)/len(g))
    o.sort(); return o[int(T*.025)], o[int(T*.975)]
def show(rows, lbl, minn=10):
    if len(rows) < minn: print(f"  {lbl:<34} n={len(rows)} too few"); return
    n, h, u, ro = sc(rows); lo, hi = pb(rows)
    print(f"  {lbl:<34} n={n:<4} {h:5.1f}%  {u:+6.2f}u  ROI {ro:+6.1f}%  95CI [{lo:+6.1f},{hi:+6.1f}]")
print(f"OLD MODEL S = {len(S)} bets. Is tonight's line MOVE monotonic inside it?")
print("=" * 92)
for lo, hi, lbl in ((-9, -0.6, "moved DOWN 1+"), (-0.6, 0.4, "unchanged"),
                    (0.4, 1.4, "up 1.0"), (1.4, 9, "up 2.0+")):
    show([r for r in S if lo <= r["moved"] < hi], f"  {lbl}")
print("")
print("  monotonic would read: down >= unchanged > up1 > up2. anything else and a TIER is")
print("  fitting noise, even if the PASS/FAIL split itself is real.")
print("")
print("=" * 92)
print("  STAKING SCHEMES ON THE SAME 75 BETS")
print("=" * 92)
P = [r for r in S if r["net"]]; F = [r for r in S if not r["net"]]
_, _, up, _ = sc(P); _, _, uf, _ = sc(F)
for lbl, stP, stF in (("flat 1u on all 75 (today)", 1, 1),
                      ("gate 5 as a FILTER (skip fails)", 1, 0),
                      ("TIER 2u pass / 1u fail", 2, 1),
                      ("TIER 3u pass / 1u fail", 3, 1)):
    staked = stP*len(P) + stF*len(F)
    prof = stP*up + stF*uf
    print(f"  {lbl:<34} risk {staked:>4}u   profit {prof:+7.2f}u   ROI {100*prof/staked:+6.1f}%")
print("")
print("  ROI is profit per unit RISKED. tiering buys more profit only by risking more, and on an")
print("  edge whose interval barely clears zero that is leverage, not improvement.")
print("")
print("=" * 92)
print("  THE DECIDING QUESTION - is the FAIL group worth 1u at all?")
print("=" * 92)
show(F, "  gate 5 FAIL (starred but raised tonight)")
print("")
print("  if this interval covers zero comfortably, a 1u tier on it is a coin-flip bet funded")
print("  from the same bankroll as the good one.")
