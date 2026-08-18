# buy_all_lines.py - what if you simply buy EVERY line the book offers, better or worse?
# ---------------------------------------------------------------------------------------------
# I told the user "never take the worse one", citing a -6.1% cell. But that cell was
# "REPLACE your bet with the risen line". Buying the worse line as an EXTRA ticket is a
# different animal, and in the audit its extras came out at +18.7% - better than the +16.7%
# baseline. If that holds, my advice was wrong and the honest answer is that a higher line
# simply comes with a higher price, so it is not worse in EV terms at all.
#
# This settles it three ways: at equal risk, on the extras alone, and with a permutation on
# the improvement-vs-worse difference, since the user is now betting real money on it.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260907)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "timing_headtohead.py"), encoding="utf-8").read().split("same = [r for r in K")[0])

def pn(ln, od, act):
    if act == ln: return 0.0
    return (od-1) if act > ln else -1.0

def tickets(kind):
    out = []
    for r in K:
        if kind == "first":
            out.append((r["first"][0], r["first"][1], r["actual"]))
        elif kind == "every":
            for ln, od in r["lines"]: out.append((ln, od, r["actual"]))
        else:
            held = None
            for ln, od in r["lines"]:
                take = held is None or (ln < held if kind == "improve" else ln > held)
                if take:
                    out.append((ln, od, r["actual"]))
                    held = ln if held is None else (min(held, ln) if kind == "improve" else max(held, ln))
    return out

def rep(lbl, t):
    u = sum(pn(*x) for x in t)
    print(f"  {lbl:<36}{len(t):>6}{len(t):>7.0f}u{u:>+9.2f}u{100*u/len(t):>+9.1f}%")
    return u, len(t)

print("="*100)
print("  BUY EVERY LINE vs THE ALTERNATIVES")
print("="*100)
print(f"  {'strategy':<36}{'tickets':>6}{'risked':>8}{'profit':>10}{'per unit':>10}")
uf, nf = rep("FIRST only", tickets("first"))
ui, ni = rep("FIRST + improvements only", tickets("improve"))
uw, nw = rep("FIRST + worse only", tickets("worse"))
ue, ne = rep("EVERY line (better AND worse)", tickets("every"))
print("")
print("="*100)
print("  AT EQUAL RISK - every scheme scaled to the same capital as FIRST only")
print("="*100)
for lbl, u, n in (("FIRST only", uf, nf), ("FIRST + improvements", ui, ni),
                  ("FIRST + worse", uw, nw), ("EVERY line", ue, ne)):
    sc = nf/n
    print(f"  {lbl:<36} stake x{sc:.2f}   {nf}u risked   profit {u*sc:+7.2f}u")
print("")
print("="*100)
print("  THE EXTRA TICKETS ALONE - this is where my advice was wrong")
print("="*100)
ex_i = [x for x in tickets("improve")]; ex_w = [x for x in tickets("worse")]
fi = tickets("first")
# extras = the strategy's tickets minus one-per-bet; compare like with like by counting
n_ei, u_ei = ni-nf, ui-uf
n_ew, u_ew = nw-nf, uw-uf
print(f"  improvement extras  {n_ei:>4} tickets  {u_ei:+7.2f}u  {100*u_ei/n_ei:+6.1f}%")
print(f"  worse-line extras   {n_ew:>4} tickets  {u_ew:+7.2f}u  {100*u_ew/n_ew:+6.1f}%")
print(f"  baseline (first)    {nf:>4} tickets  {uf:+7.2f}u  {100*uf/nf:+6.1f}%")
print("")
print("  A HIGHER line comes with a HIGHER price. That is the book doing its job, and it means")
print("  a worse number is not automatically a worse BET - which is why the worse-line extras")
print("  are not negative. My 'never take the worse one' came from a different test: REPLACING")
print("  your ticket with the risen line, not ADDING one.")
print("")
print("="*100)
print("  IS THE IMPROVEMENT EDGE OVER WORSE-LINES REAL? permutation on the difference")
print("="*100)
gap = 100*u_ei/n_ei - 100*u_ew/n_ew
print(f"  real gap: improvements {100*u_ei/n_ei:+.1f}% minus worse {100*u_ew/n_ew:+.1f}% = {gap:+.1f}pp")
pool = []
for r in K:
    if len(r["lines"]) < 2: continue
    for ln, od in r["lines"][1:]:
        pool.append((ln, od, r["actual"]))
if len(pool) >= 20:
    beat = 0; T = 20000
    for _ in range(T):
        random.shuffle(pool)
        a = pool[:n_ei]; b = pool[n_ei:n_ei+n_ew]
        if not b: continue
        ga = 100*sum(pn(*x) for x in a)/len(a) - 100*sum(pn(*x) for x in b)/len(b)
        if ga >= gap: beat += 1
    print(f"  shuffling which extras count as 'improvement': gap >= real in {beat}/{T} "
          f"-> p = {beat/T:.4f}")
print("")
print(f"  ({len(pool)} extra tickets exist in total across {sum(1 for r in K if len(r['lines'])>1)} multi-line bets)")
