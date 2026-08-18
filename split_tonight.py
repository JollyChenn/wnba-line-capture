import os, collections, statistics, random
__file__ = os.path.join(os.getcwd(), "split.py")
random.seed(3)
src = open("ping_vs_open.py", encoding="utf-8").read()
exec(src.split('print(f"{len(R)} MODEL S bets regradable')[0])
def sc(rows, wk, ok):
    n = len(rows); w = sum(1 for r in rows if r[wk])
    u = sum((r[ok]-1) if r[wk] else -1.0 for r in rows)
    return n, 100*w/n, u, 100*u/n
def pb(rows, wk, ok, T=3000):
    bp = collections.defaultdict(list)
    for r in rows: bp[r["pl"]].append(r)
    k = list(bp); o = []
    for _ in range(T):
        g = [x for p in [random.choice(k) for _ in k] for x in bp[p]]
        o.append(100*sum((x[ok]-1) if x[wk] else -1.0 for x in g)/len(g))
    o.sort(); return o[75], o[2924]
print("MODEL S at the PING price, split by what the line did since TONIGHT opened:")
print("")
for lo, hi, lbl in ((-9, -0.4, "line moved DOWN (book softer)"),
                    (-0.4, 0.4, "line UNCHANGED"),
                    (0.4, 9, "line moved UP (book repriced)")):
    g = [r for r in R if lo <= r["moved"] < hi]
    if len(g) < 10: print(f"  {lbl:<38} n={len(g)} too few"); continue
    n, h, u, ro = sc(g, "p_w", "p_o"); l, hh = pb(g, "p_w", "p_o")
    print(f"  {lbl:<38} n={n:<4} {h:5.1f}%  {u:+6.2f}u  ROI {ro:+6.1f}%  95CI [{l:+6.1f},{hh:+6.1f}]")
print("")
g = [r for r in R if r["moved"] <= 0]
n, h, u, ro = sc(g, "p_w", "p_o"); l, hh = pb(g, "p_w", "p_o")
print(f"  {'NOT raised tonight = the fix':<38} n={n:<4} {h:5.1f}%  {u:+6.2f}u  ROI {ro:+6.1f}%  95CI [{l:+6.1f},{hh:+6.1f}]")
g2 = [r for r in R if r["moved"] > 0]
n2, h2, u2, ro2 = sc(g2, "p_w", "p_o")
print(f"  {'raised tonight = what we would drop':<38} n={n2:<4} {h2:5.1f}%  {u2:+6.2f}u  ROI {ro2:+6.1f}%")
print("")
print(f"  volume kept: {len(g)} of {len(R)} ({100*len(g)/len(R):.0f}%)")
