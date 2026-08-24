# stake_risk.py - if we commit real money NOW, what does the next stretch actually look like?
# ---------------------------------------------------------------------------------------------
# The question is not "are we winning" - five straight wins guarantees it feels that way. It is:
#   1 how much do 18 bets at 11-7 actually tell us about the true win rate?
#   2 starting today, what is the DISTRIBUTION of the next 20 and 40 bets - not the average, the
#     spread, and specifically how deep the drawdowns go?
#   3 how likely is it that we are simply at the top of a variance swing right now?
#
# That third one matters most and is the easiest to fool yourself about. A run of five wins is
# NOT rare: even a break-even coin at these prices throws one every ~20 sequences. If we size up
# after a streak, we are systematically buying at local peaks - the streak itself carries no
# information about the next bet, but it strongly biases OUR judgement about it.
#
# Everything below uses the real live prices from model_forward, not an assumed 1.85.
import csv, os, sys, math, random, statistics, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260824)
D = os.path.dirname(os.path.abspath(__file__))
SIG = ("flip", "hotover", "overshoot"); MK = ("pra", "pr", "pts")
rows = [r for r in csv.DictReader(open(os.path.join(D, "model_forward.csv"), encoding="utf-8"))
        if r.get("src") in SIG and r.get("market") in MK
        and (r.get("result") or "").upper() in ("WIN", "LOSS")]
odds = [float(r["odds"]) for r in rows]
wins = [1 if (r["result"] or "").upper() == "WIN" else 0 for r in rows]
n, w = len(wins), sum(wins)
mo = statistics.mean(odds)
be = 1/mo
pnl = sum((o-1) if x else -1.0 for o, x in zip(odds, wins))
print(f"LIVE SO FAR: n={n}  {w}-{n-w}  {100*w/n:.1f}%  {pnl:+.2f}u  ROI {100*pnl/n:+.1f}%")
print(f"  mean price {mo:.3f} -> breakeven {100*be:.1f}%")
# streak
st = 0
for x in reversed(wins):
    if x: st += 1
    else: break
print(f"  current winning streak: {st}")
print("")
print("="*96)
print("  1. WHAT 18 BETS ACTUALLY TELL US - the honest interval on the true win rate")
print("="*96)
# Jeffreys interval, and a bootstrap on ROI
lo_p, hi_p = None, None
def beta_q(a, b, q, it=200000):
    xs = sorted(random.betavariate(a, b) for _ in range(20000))
    return xs[int(len(xs)*q)]
a, b = w + 0.5, (n - w) + 0.5
lo_p, hi_p = beta_q(a, b, 0.025), beta_q(a, b, 0.975)
print(f"  true win rate, 95% credible: {100*lo_p:.1f}% .. {100*hi_p:.1f}%   (breakeven {100*be:.1f}%)")
print(f"  P(true rate is BELOW breakeven) = "
      f"{sum(1 for _ in range(20000) if random.betavariate(a,b) < be)/20000:.1%}")
print("  an interval that wide is the whole answer to 'is it proven'. it is not.")
print("")
print("="*96)
print("  2. THE NEXT 20 AND 40 BETS, starting from zero, at these prices")
print("="*96)
def sim(p, k, T=40000):
    fin, dd, prof = [], [], 0
    for _ in range(T):
        eq = peak = worst = 0.0
        for i in range(k):
            o = random.choice(odds)
            eq += (o-1) if random.random() < p else -1.0
            peak = max(peak, eq); worst = min(worst, eq - peak)
        fin.append(eq); dd.append(worst)
    fin.sort(); dd.sort()
    return fin, dd
print(f"  {'assumed true rate':<28}{'bets':>6}{'P(profit)':>11}{'median':>9}{'worst 5%':>10}{'typical max DD':>16}")
for p, lbl in ((0.658, "65.8% (the backtest)"), (0.611, "61.1% (live so far)"),
               (be,    f"{100*be:.1f}% (no edge)"), (0.50, "50% (broken)")):
    for k in (20, 40):
        fin, dd = sim(p, k)
        pw = sum(1 for x in fin if x > 0)/len(fin)
        print(f"  {lbl if k==20 else '':<28}{k:>6}{pw:>10.0%}{fin[len(fin)//2]:>+9.1f}u"
              f"{fin[int(len(fin)*0.05)]:>+10.1f}u{dd[len(dd)//2]:>+15.1f}u")
print("")
print("  'typical max DD' is the MEDIAN worst drawdown - half of all runs are deeper than this.")
print("  even a genuinely 65.8% model spends time underwater; that is not the model breaking.")
print("")
print("="*96)
print("  3. IS A 5-WIN STREAK EVIDENCE OF ANYTHING?")
print("="*96)
for p, lbl in ((0.658, "a 65.8% model"), (be, "a NO-EDGE coin")):
    hit = 0
    for _ in range(40000):
        seq = [random.random() < p for _ in range(n)]
        s = 0; best = 0
        for x in seq:
            s = s + 1 if x else 0
            best = max(best, s)
        if best >= st: hit += 1
    print(f"  P(a run of {st}+ somewhere in {n} bets) under {lbl:<16} = {hit/40000:.0%}")
print("  if a coin does it this often, the streak is not information - it is scenery.")
print("")
print("="*96)
print("  4. WHAT SIZING SURVIVES BEING WRONG")
print("="*96)
print("  the real question is not expected profit, it is: what stake leaves you playing if the")
print("  edge turns out to be zero? at 1u flat, the 5%-worst 40-bet outcome under NO EDGE is")
fin, dd = sim(be, 40)
print(f"    {fin[int(len(fin)*0.05)]:+.1f}u final, median worst drawdown {dd[len(dd)//2]:+.1f}u")
print("  multiply both by your unit size. if that number would stop you betting, the unit is")
print("  too big - because that is the outcome you must be able to absorb WITHOUT quitting,")
print("  since quitting mid-experiment is how you pay the costs and never collect the edge.")
