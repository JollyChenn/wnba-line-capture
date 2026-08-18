# audit_improvement.py - the user has now BET this rule, so audit it properly.
# ---------------------------------------------------------------------------------------------
# I reported "FIRST + add each improvement" at +20.9% against +16.1% for first-only, flagged the
# correlation caveat, and the user went and took two lines on Ogunbowale. That worked - she went
# PR 21 and cleared every number the book offered - but one win says nothing. Before this becomes
# a habit it needs the same treatment everything else got:
#   1 a control: does adding tickets in the WRONG direction look just as good?
#   2 outlier sensitivity: is the gap carried by two or three lucky multi-ticket nights?
#   3 the real cost of correlation: how often does a multi-ticket player lose EVERY ticket?
#   4 drawdown, since that is where concentration actually hurts
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260906)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "timing_headtohead.py"), encoding="utf-8").read().split("same = [r for r in K")[0])

def strat(kind):
    """returns a list of (line, odds, actual, player-key) tickets"""
    out = []
    for r in K:
        if kind == "first":
            out.append((r["first"][0], r["first"][1], r["actual"], r["pl"], r["date"]))
        elif kind == "last":
            out.append((r["last"][0], r["last"][1], r["actual"], r["pl"], r["date"]))
        elif kind == "improve":
            held = None
            for ln, od in r["lines"]:
                if held is None or ln < held:
                    out.append((ln, od, r["actual"], r["pl"], r["date"])); held = ln
        elif kind == "worse":
            held = None
            for ln, od in r["lines"]:
                if held is None or ln > held:
                    out.append((ln, od, r["actual"], r["pl"], r["date"])); held = ln
        elif kind == "every":
            for ln, od in r["lines"]:
                out.append((ln, od, r["actual"], r["pl"], r["date"]))
    return out

def pnl(t):
    ln, od, act = t[0], t[1], t[2]
    if act == ln: return 0.0
    return (od-1) if act > ln else -1.0
def tot(ts_): return sum(pnl(t) for t in ts_)
def roi(ts_): return tot(ts_)/len(ts_) if ts_ else 0.0

print("="*100)
print("  1. THE CONTROL - is it the DIRECTION, or just having more tickets?")
print("="*100)
for lbl, k in (("FIRST only", "first"), ("FIRST + improvements (lower)", "improve"),
               ("FIRST + worse lines (control)", "worse"), ("EVERY line", "every")):
    t_ = strat(k)
    print(f"  {lbl:<34} {len(t_):>4} tickets  {tot(t_):+8.2f}u  ROI {100*roi(t_):+6.1f}%")
imp, wor, fst = strat("improve"), strat("worse"), strat("first")
print(f"\n  improvements add {len(imp)-len(fst)} tickets worth {tot(imp)-tot(fst):+.2f}u "
      f"= {100*(tot(imp)-tot(fst))/(len(imp)-len(fst)):+.1f}% on the extras alone")
print(f"  worse lines add  {len(wor)-len(fst)} tickets worth {tot(wor)-tot(fst):+.2f}u "
      f"= {100*(tot(wor)-tot(fst))/(len(wor)-len(fst)):+.1f}% on the extras alone")
print("")
print("="*100)
print("  2. OUTLIER SENSITIVITY - drop the best and worst PLAYER-NIGHTS and re-check")
print("="*100)
bynight = collections.defaultdict(list)
for t in imp: bynight[(t[4], t[3])].append(t)
nights = sorted(bynight.items(), key=lambda kv: tot(kv[1]))
for drop in (0, 1, 2, 3):
    keep = nights[drop:len(nights)-drop] if drop else nights
    tk = [t for _, v in keep for t in v]
    fk = [t for t in fst if (t[4], t[3]) in dict(keep)]
    print(f"  drop {drop} worst and {drop} best nights: improve {100*roi(tk):+6.1f}%   "
          f"first {100*roi(fk):+6.1f}%   gap {100*(roi(tk)-roi(fk)):+5.1f}pp")
print("")
print("="*100)
print("  3. THE CORRELATION COST - when you hold 2+ tickets on one player, what happens?")
print("="*100)
multi = {k: v for k, v in bynight.items() if len(v) > 1}
allw = sum(1 for v in multi.values() if all(pnl(t) > 0 for t in v))
alll = sum(1 for v in multi.values() if all(pnl(t) < 0 for t in v))
split = len(multi) - allw - alll
print(f"  player-nights with 2+ tickets: {len(multi)}")
print(f"    ALL tickets won   {allw:>3}  ({100*allw/len(multi):4.0f}%)   <- tonight's Ogunbowale")
print(f"    ALL tickets lost  {alll:>3}  ({100*alll/len(multi):4.0f}%)   <- the concentration cost")
print(f"    split             {split:>3}  ({100*split/len(multi):4.0f}%)   <- the lines straddled her score")
print(f"  so {100*(allw+alll)/len(multi):.0f}% of the time the extra ticket just doubles the first one.")
print("")
print("="*100)
print("  4. DRAWDOWN - concentration shows up here, not in the ROI")
print("="*100)
for lbl, k in (("FIRST only", "first"), ("FIRST + improvements", "improve")):
    t_ = sorted(strat(k), key=lambda x: x[4])
    eq = peak = dd = 0.0; run = 0; worst = 0
    for t in t_:
        p = pnl(t); eq += p
        peak = max(peak, eq); dd = min(dd, eq-peak)
        run = 0 if p > 0 else run+1; worst = max(worst, run)
    print(f"  {lbl:<26} {len(t_):>4} tickets  worst drawdown {dd:+7.2f}u  longest losing run {worst}")
print("")
print("  and at EQUAL RISK, scaling improvements down to the same capital as first-only:")
sc = len(fst)/len(imp)
print(f"    FIRST only            {len(fst)}u risked   {tot(fst):+.2f}u")
print(f"    improvements x{sc:.2f}     {len(fst)}u risked   {tot(imp)*sc:+.2f}u")
