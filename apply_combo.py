#!/usr/bin/env python
"""Apply the 'volatile & star -> UNDER' combo to OUR actual graded bets — both ways:
  - LEAKED   (volatility from full-season CV = the version that showed 71%)
  - LEAK-FREE (volatility from TRAILING CV only = honest)
so you can see the leak on our own history. star = trailing median >=15. Pure stdlib."""
import csv
import statistics
import sys
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def nd(d):
    return ''.join(c for c in str(d) if c.isdigit())[:8]


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


gdate = {r["game_id"]: nd(r.get("date", "")) for r in csv.DictReader(open("data/games_2026.csv", encoding="utf-8"))}
log = defaultdict(list)
for r in csv.DictReader(open("data/box_2026.csv", encoding="utf-8")):
    d = gdate.get(r["game_id"])
    if not d:
        continue
    try:
        log[r["player"].lower()].append((d, float(r["pts"])))
    except (ValueError, TypeError):
        pass
for pl in log:
    log[pl].sort(key=lambda t: t[0])

# full-season CV per player (the LEAKY one) + threshold
fcv = {pl: statistics.pstdev([p for _, p in gl]) / statistics.mean([p for _, p in gl])
       for pl, gl in log.items() if len(gl) >= 8 and statistics.mean([p for _, p in gl]) >= 8}
fthr = statistics.median(list(fcv.values()))

# global TRAILING CV threshold (no lookahead)
all_tcv = []
for pl, gl in log.items():
    pts = [p for _, p in gl]
    for i in range(5, len(pts)):
        w = pts[max(0, i - 10):i]
        all_tcv.append(statistics.pstdev(w) / statistics.mean(w) if statistics.mean(w) else 0)
tthr = statistics.median(all_tcv)


def trailing(pl, bdate):
    prior = [p for d, p in log.get(pl, []) if d < bdate]
    if len(prior) < 5:
        return None
    w = prior[-10:]
    return statistics.median(w), (statistics.pstdev(w) / statistics.mean(w) if statistics.mean(w) else 0)


bets = []
for r in csv.DictReader(open("graded_bets.csv", encoding="utf-8")):
    res = r.get("result", "")
    if res not in ("WIN", "loss", "LOSS"):
        continue
    pl, bdate = r["player"].lower(), nd(r["date"])
    t = trailing(pl, bdate)
    if not t:
        continue
    med, tcv = t
    bets.append(dict(player=r["player"], side=r.get("side"), win=(res == "WIN"), pnl=fnum(r.get("pnl")) or 0,
                     star=med >= 15, vol_trail=tcv >= tthr,
                     vol_full=(fcv.get(pl) is not None and fcv[pl] >= fthr), med=med, tcv=tcv))


def rec(items):
    n = len(items)
    w = sum(b["win"] for b in items)
    pnl = sum(b["pnl"] for b in items)
    return f"{w}-{n - w} ({100 * w / n:.0f}%)  {pnl:+.2f}u" if n else "— none —"


print(f"our settled bets matched to box history: {len(bets)}")
print(f"thresholds: trailing-CV {tthr:.2f}, full-season-CV {fthr:.2f}\n")

for tag, key in [("LEAK-FREE  (trailing CV — honest)", "vol_trail"), ("LEAKED     (full-season CV — the '71%')", "vol_full")]:
    stars = [b for b in bets if b["star"] and b[key]]
    unders = [b for b in stars if b["side"] == "Under"]
    print(f"=== {tag} ===")
    print(f"  our bets on volatile-stars (any side): {rec(stars)}")
    print(f"  of those, the combo's pick = UNDER   : {rec(unders)}")
    print()

print("the volatile-star bets in our history (leak-free flag):")
for b in sorted([b for b in bets if b["star"] and b["vol_trail"]], key=lambda b: b["player"]):
    print(f"  {b['player'][:20]:<20} {b['side']:<5} med {b['med']:.0f} cv {b['tcv']:.2f} -> {'WIN ' if b['win'] else 'loss'} {b['pnl']:+.2f}u")
