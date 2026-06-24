#!/usr/bin/env python
"""Re-do the fade with the REAL other-side odds (not flat 1.80). For each graded bet, look up the
opposite side's actual 1xbet odds from xbet_snapshots (same player+market+line). Fade P&L then uses
the price you'd ACTUALLY get. Reports coverage (how many bets had a real complement captured)."""
import csv
import statistics
import sys
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


snap = defaultdict(list)
for r in csv.DictReader(open("xbet_snapshots.csv", encoding="utf-8")):
    o = fnum(r.get("odds"))
    ln = fnum(r.get("line"))
    if o and ln is not None:
        snap[(r["player"].lower(), r.get("market"), ln, r.get("side"))].append(o)


def comp_odds(player, mk, line, side):
    opp = "Over" if side == "Under" else "Under"
    v = snap.get((player.lower(), mk, line, opp), [])
    return statistics.median(v) if v else None


sig = defaultdict(list)
matched = 0
for r in csv.DictReader(open("graded_bets.csv", encoding="utf-8")):
    res = r.get("result", "")
    if res not in ("WIN", "loss", "LOSS"):
        continue
    line = fnum(r.get("line"))
    co = comp_odds(r["player"], r.get("market"), line, r.get("side")) if line is not None else None
    if co:
        matched += 1
    sig[r.get("src")].append((res == "WIN", fnum(r.get("pnl")) or 0, fnum(r.get("odds")) or 1.83, co))

total = sum(len(v) for v in sig.values())
print(f"{total} bets · {matched} have a REAL complement odds captured ({100*matched/total:.0f}% coverage)\n")
print(f"{'signal':<12}{'n(real)':>8}{'fade W-L':>10}{'avg fade odd':>13}{'FADE @REAL':>12}{'(vs flat 1.80)':>16}")
print("-" * 72)
allreal = []
for s, items in sorted(sig.items()):
    real = [b for b in items if b[3]]
    if not real:
        continue
    allreal += real
    fw = sum(1 for b in real if not b[0])
    fpnl = sum(((b[3] - 1) if not b[0] else -1.0) for b in real)
    flat = sum((0.80 if not b[0] else -1.0) for b in real)
    avg_odd = statistics.mean([b[3] for b in real])
    print(f"{s:<12}{len(real):>8}{f'{fw}-{len(real)-fw}':>10}{avg_odd:>13.2f}{fpnl:>+11.2f}u{flat:>+15.2f}u")

fw = sum(1 for b in allreal if not b[0])
fpnl = sum(((b[3] - 1) if not b[0] else -1.0) for b in allreal)
flat = sum((0.80 if not b[0] else -1.0) for b in allreal)
print("-" * 72)
print(f"{'ALL (real)':<12}{len(allreal):>8}{f'{fw}-{len(allreal)-fw}':>10}"
      f"{statistics.mean([b[3] for b in allreal]):>13.2f}{fpnl:>+11.2f}u{flat:>+15.2f}u")
print(f"\nfade win-rate {100*fw/len(allreal):.0f}%; break-even at avg fade odds = {100/statistics.mean([b[3] for b in allreal]):.0f}%")
