#!/usr/bin/env python
"""Which ODDS MOVEMENT (entry price vs the close) makes money — straight vs faded.
Positive odds_clv = our price shortened toward the close (market moved TO our side).
Negative = it lengthened (market moved AGAINST us). Fade P&L = betting the other side."""
import csv
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


g = []
for r in csv.DictReader(open("graded_bets.csv", encoding="utf-8")):
    res = (r.get("result") or "").strip().upper()
    if res.startswith("WIN"):
        r["_win"] = 1
    elif res in ("LOSS", "LOSE", "L"):
        r["_win"] = 0
    else:
        continue
    g.append(r)


def stat(items):
    n = len(items)
    w = sum(b["_win"] for b in items)
    spnl = sum(fnum(b.get("pnl")) or 0 for b in items)
    fpnl = sum(((fnum(b.get("odds")) or 0) - 1 if b["_win"] == 0 else -1.0) for b in items)
    return n, w, n - w, spnl, fpnl


buckets = [
    ("strong AGAINST  (odds lengthened ≥2%)", lambda v: v is not None and v <= -0.02),
    ("mild against    (0 to −2%)",            lambda v: v is not None and -0.02 < v < 0),
    ("FLAT           (no move)",              lambda v: v == 0),
    ("mild toward     (0 to +2%)",            lambda v: v is not None and 0 < v < 0.02),
    ("strong TOWARD   (odds shortened ≥2%)",  lambda v: v is not None and v >= 0.02),
    ("no CLV data",                           lambda v: v is None),
]

print(f"{'odds movement (entry → close)':<40}{'n':>4}{'straight':>11}{'P&L':>9}{'fade P&L':>10}")
print("-" * 74)
for lab, pred in buckets:
    items = [b for b in g if pred(fnum(b.get("odds_clv")))]
    if not items:
        continue
    n, w, l, sp, fp = stat(items)
    print(f"{lab:<40}{n:>4}{f'{w}-{l}':>11}{sp:>+8.2f}u{fp:>+9.2f}u")
n, w, l, sp, fp = stat(g)
print("-" * 74)
print(f"{'ALL':<40}{n:>4}{f'{w}-{l}':>11}{sp:>+8.2f}u{fp:>+9.2f}u")

# does odds movement catch the overshoot trap? (it shouldn't — different failure mode)
ov = [b for b in g if b.get("src") == "overshoot"]
print("\novershoot-overs — do they show the line moving against us? (the trap tell?)")
for lab, pred in buckets[:5]:
    items = [b for b in ov if pred(fnum(b.get("odds_clv")))]
    if items:
        n, w, l, sp, fp = stat(items)
        print(f"  {lab:<40}{n:>3}  {w}-{l}  straight {sp:+.2f}u")
