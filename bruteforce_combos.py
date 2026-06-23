#!/usr/bin/env python
"""Brute-force EVERY single/pair/triplet of bet filters on the graded board, ranked by P&L.
THEN the only thing that makes this honest: a SHUFFLE CONTROL — re-run the entire search on
randomized win/loss labels K times and see the best P&L chance alone produces. If the real
best isn't clearly above the shuffle distribution, the 'winning' combo is overfitting, not edge.
Pure stdlib. (clv features are hindsight — flagged.)"""
import bisect
import csv
import itertools
import random
import statistics
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
random.seed(7)


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


bets = []
for r in csv.DictReader(open("graded_bets.csv", encoding="utf-8")):
    res = (r.get("result") or "").strip().upper()
    if res.startswith("WIN"):
        win = 1
    elif res in ("LOSS", "LOSE", "L"):
        win = 0
    else:
        continue
    side, mk, tier, src = r.get("side"), r.get("market"), r.get("tier"), r.get("src")
    line, odds, clv = fnum(r.get("line")) or 0, fnum(r.get("odds")) or 0, fnum(r.get("odds_clv"))
    f = {
        "Under": side == "Under", "Over": side == "Over",
        "pts": mk == "pts", "combo(pra/pr/pa)": mk in ("pra", "pr", "pa"),
        "STRONG": tier == "STRONG", "THIN": tier == "THIN", "SOLID": tier == "SOLID",
        "clv>0*": clv is not None and clv > 1e-9, "clv<0*": clv is not None and clv < -1e-9,
        "line>=18": line >= 18, "line<18": line < 18,
        "odds>=1.9": odds >= 1.9, "odds<1.9": odds < 1.9,
        "src=model": src == "model", "src=newunder": src == "newunder",
        "src=overshoot": src == "overshoot", "src=hotover": src == "hotover",
    }
    bets.append((f, win, fnum(r.get("pnl")) or 0))

FEATS = list(bets[0][0].keys())
N = len(bets)
fset = {ft: set(i for i, (f, _, _) in enumerate(bets) if f[ft]) for ft in FEATS}
wins = [b[1] for b in bets]
pnls = [b[2] for b in bets]

MIN = 8
combos = []
for k in (1, 2, 3):
    for c in itertools.combinations(FEATS, k):
        idx = set(range(N))
        for ft in c:
            idx &= fset[ft]
            if len(idx) < MIN:
                break
        if len(idx) >= MIN:
            combos.append((c, list(idx)))

print(f"{N} graded bets · {len(FEATS)} features · {len(combos)} combos (n>={MIN}) searched\n")

real = sorted(((c, len(idx), sum(wins[i] for i in idx), sum(pnls[i] for i in idx)) for c, idx in combos),
              key=lambda x: x[3], reverse=True)
print("TOP 8 combos by P&L (IN-SAMPLE — before the reality check):")
for c, n, w, p in real[:8]:
    print(f"  {p:+6.2f}u  {w}-{n - w} ({100 * w / n:3.0f}%)  n={n:>2}  ::  {' & '.join(c)}")

K = 400
order = list(range(N))
sh_best = []
for _ in range(K):
    random.shuffle(order)
    P = [pnls[order[i]] for i in range(N)]
    sh_best.append(max(sum(P[i] for i in idx) for c, idx in combos))
sh_best.sort()
realbest = real[0][3]
pctl = 100 * bisect.bisect_left(sh_best, realbest) / K
print(f"\nSHUFFLE CONTROL ({K}× random labels) — best P&L chance alone finds:")
print(f"  median {statistics.median(sh_best):+.2f}u · 95th pct {sh_best[int(0.95 * K)]:+.2f}u · max {sh_best[-1]:+.2f}u")
print(f"  REAL best {realbest:+.2f}u  →  beats {pctl:.0f}% of random searches")
print("  VERDICT: " + ("REAL — real best clears the chance ceiling" if pctl >= 95
                        else f"OVERFIT — pure chance produces combos this good (real best is only the {pctl:.0f}th pct of noise). NOT an edge."))
