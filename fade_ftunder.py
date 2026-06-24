#!/usr/bin/env python
"""Is FTUNDER (newunder) 'the perfect fade'? Test it honestly: bet-record vs fade-record overall
and by market/CLV, + is the live underperformance REAL or just variance vs the 58.9% backtest?
Pure stdlib."""
import csv
import math
import statistics
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
    if r.get("src") != "newunder":
        continue
    res = r.get("result", "")
    if res not in ("WIN", "loss", "LOSS"):
        continue
    g.append(dict(win=(res == "WIN"), pnl=fnum(r.get("pnl")) or 0, odds=fnum(r.get("odds")) or 0,
                  mk=r.get("market"), line=fnum(r.get("line")) or 0, clv=fnum(r.get("odds_clv"))))


def line(label, items):
    n = len(items)
    if not n:
        print(f"  {label:<26} —")
        return
    w = sum(b["win"] for b in items)
    pnl = sum(b["pnl"] for b in items)
    fade = sum(((b["odds"] - 1) if not b["win"] else -1.0) for b in items)
    print(f"  {label:<26} {w:>2}-{n-w:<2} ({100*w/n:3.0f}%)  bet {pnl:+6.2f}u   FADE {n-w}-{w} {fade:+6.2f}u")


print(f"FTUNDER (newunder): {len(g)} settled bets\n")
print(f"{'cut':<26} {'record':>10}   {'bet P&L':>10}   {'FADE':>14}")
line("ALL", g)
print("  --- by market ---")
line("pts", [b for b in g if b["mk"] == "pts"])
line("combo (pr/pa/pra)", [b for b in g if b["mk"] in ("pr", "pa", "pra")])
print("  --- by odds-CLV (the price test) ---")
line("beat/flat close (CLV>=0)", [b for b in g if b["clv"] is not None and b["clv"] >= 0])
line("worse close (CLV<0)", [b for b in g if b["clv"] is not None and b["clv"] < 0])
print("  --- by line size ---")
line("line >= 15", [b for b in g if b["line"] >= 15])
line("line < 15", [b for b in g if b["line"] < 15])

# is the underperformance REAL or variance? vs the 58.9% backtest workhorse
n = len(g)
w = sum(b["win"] for b in g)
p = w / n
BT = 0.589
se = math.sqrt(BT * (1 - BT) / n)
z = (p - BT) / se
print(f"\nLIVE {w}-{n-w} = {p*100:.0f}%  vs the 58.9% backtest 'workhorse':")
print(f"  z = {z:+.2f}  (p≈{2*(1-0.5*(1+math.erf(abs(z)/math.sqrt(2)))):.2f}) — "
      f"{'SIGNIFICANT drop (signal may be broken)' if abs(z) >= 2 else 'NOT significant — could be variance that REVERTS to winning (fading it would then backfire)'}")
be = 100 / (sum(b['odds'] for b in g) / n)
print(f"  break-even at avg odds = {be:.0f}%.  Fade wins only if the fade rate clears it.")
