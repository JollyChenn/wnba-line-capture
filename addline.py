# addline.py - you were pinged at 18.5, you bet it, then 17.5 appears. What do you DO?
# ------------------------------------------------------------------------------------------
# "Wait and take it once" is not a rule anyone can follow - you cannot know a better number is
# coming. The real choice, once you already hold the first line, is only:
#     A  hold what you have, ignore the improvement
#     B  add the better line as a second 1u
# and there is no cash-out on 1xbet, so those are the only two.
# Also settles: is OVERSHOOT actually good, priced where you'd bet it?
import csv, os, sys, random, collections, statistics
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260928)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "gate5.py"), encoding="utf-8").read()
     .split('print(f"{len(A)} bets with gates 1+2 on')[0])
S = [r for r in A if r["star"] == "starred"]

print("=" * 96)
print("  IS OVERSHOOT GOOD? (Model S bets, at the price you are pinged)")
print("=" * 96)
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
for s in ("overshoot", "flip", "hotover"):
    g = [r for r in S if r["src"] == s]
    if len(g) < 10: print(f"  {s:<28} n={len(g)} too few"); continue
    n, h, u, ro = sc(g); lo, hi = pb(g)
    print(f"  {s:<28} n={n:<4} {h:5.1f}%  {u:+6.2f}u  ROI {ro:+6.1f}%  95CI [{lo:+6.1f},{hi:+6.1f}]")
g = [r for r in S if r["src"] == "overshoot" and r["net"]]
if len(g) >= 10:
    n, h, u, ro = sc(g); lo, hi = pb(g)
    print(f"  {'overshoot + gate5':<28} n={n:<4} {h:5.1f}%  {u:+6.2f}u  ROI {ro:+6.1f}%  95CI [{lo:+6.1f},{hi:+6.1f}]")
print("")
print("=" * 96)
print("  YOU ALREADY HOLD THE FIRST LINE. DOES ADDING A BETTER ONE PAY?")
print("=" * 96)
multi = 0; firstu = 0.0; addu = 0.0; addn = 0; holdn = 0
rows_add = []
for r in S:
    q = seq.get((r["pl"], r["mk"], r["gt"]), [])
    if not q: continue
    now = pgrow.get((r["pl"], r["gt"]))
    if not now: continue
    act = now[r["mk"]]
    # the sequence of DISTINCT lines as they appeared
    ordered = []
    for t, ln, od in q:
        if not ordered or ordered[-1][0] != ln: ordered.append((ln, od))
    first_ln, first_od = ordered[0]
    if act == first_ln: continue
    holdn += 1
    firstu += (first_od - 1) if act > first_ln else -1.0
    # every LATER line that is BETTER (lower) than what you already hold
    for ln, od in ordered[1:]:
        if ln < first_ln and act != ln:
            multi += 1; addn += 1
            addu += (od - 1) if act > ln else -1.0
            rows_add.append(dict(pl=r["pl"], od=od, won=act > ln))
print(f"  bets where a BETTER line later appeared: {multi} across {holdn} Model S bets")
print("")
print(f"  A  hold the first ping only        {holdn} bets  {firstu:+7.2f}u  ROI {100*firstu/holdn:+6.1f}%")
if addn:
    print(f"  B  the ADD-ON bets on their own    {addn} bets  {addu:+7.2f}u  ROI {100*addu/addn:+6.1f}%")
    tot = firstu + addu; risk = holdn + addn
    print(f"  A+B combined                       {risk} units  {tot:+7.2f}u  ROI {100*tot/risk:+6.1f}%")
    if len(rows_add) >= 10:
        bp = collections.defaultdict(list)
        for x in rows_add: bp[x["pl"]].append(x)
        k = list(bp); o = []
        for _ in range(3000):
            g2 = [y for p in [random.choice(k) for _ in k] for y in bp[p]]
            o.append(100*sum((y["od"]-1) if y["won"] else -1.0 for y in g2)/len(g2))
        o.sort()
        print(f"     add-on 95CI [{o[75]:+.1f}, {o[2924]:+.1f}]")
print("")
print("  the add-ons are the ONLY thing you actually control after the first ping. if they are")
print("  positive on their own, taking them is a real decision, not leverage for its own sake.")
