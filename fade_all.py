#!/usr/bin/env python
"""Fade test across EVERY signal, with REALISTIC odds. We don't capture the complement side,
and 1xbet hangs ~1.80 flat both sides (break-even 55.6%). So a fade WIN pays ~0.80 and a fade
is only +EV if the fade win-rate clears 55.6% — with enough n AND statistical significance.
Shows fade P&L at flat 1.80 (realistic) and at the bet's own odds (optimistic) for contrast."""
import csv
import math
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


sig = defaultdict(list)
for r in csv.DictReader(open("graded_bets.csv", encoding="utf-8")):
    res = r.get("result", "")
    if res not in ("WIN", "loss", "LOSS"):
        continue
    sig[r.get("src")].append((res == "WIN", fnum(r.get("pnl")) or 0, fnum(r.get("odds")) or 1.83))

BE = 0.556          # 1xbet flat ~1.80 -> break-even 55.6%
FADE_ODDS = 1.80

print(f"fade odds = flat {FADE_ODDS} (break-even {BE*100:.1f}%); 'fade win%' must clear that to profit\n")
print(f"{'signal':<12}{'n':>4}{'bet W-L':>9}{'fade win%':>11}{'fade P&L@1.80':>14}{'(@own odds)':>13}{'  verdict'}")
print("-" * 78)
rows = []
for s, items in sig.items():
    n = len(items)
    w = sum(1 for b in items if b[0])
    fw = n - w                                       # fade wins when the bet loses
    fade_flat = fw * (FADE_ODDS - 1) - w * 1.0
    fade_own = sum(((b[2] - 1) if not b[0] else -1.0) for b in items)
    fwr = fw / n
    z = (fwr - BE) / math.sqrt(BE * (1 - BE) / n) if n else 0
    rows.append((s, n, w, fw, fwr, fade_flat, fade_own, z))

for s, n, w, fw, fwr, ff, fo, z in sorted(rows, key=lambda x: x[5], reverse=True):
    if fwr <= 0.5:
        v = "don't fade (signal wins)"
    elif n < 10:
        v = f"thin (n={n})"
    elif fwr > BE and z >= 1.6:
        v = "FADE clears BE + sig"
    elif fwr > BE:
        v = "clears BE but NOT sig"
    else:
        v = "fade below BE = no"
    print(f"{s:<12}{n:>4}{f'{w}-{n-w}':>9}{fwr*100:>10.0f}%{ff:>+13.2f}u{fo:>+12.2f}u   {v}")

tot = [b for v in sig.values() for b in v]
n = len(tot); w = sum(1 for b in tot if b[0]); fw = n - w
print("-" * 78)
print(f"{'BOARD':<12}{n:>4}{f'{w}-{n-w}':>9}{fw/n*100:>10.0f}%{fw*(FADE_ODDS-1)-w:>+13.2f}u"
      f"{sum(((b[2]-1) if not b[0] else -1.0) for b in tot):>+12.2f}u   {'fade whole board?'}")
