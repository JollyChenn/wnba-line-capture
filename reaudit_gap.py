# reaudit_gap.py - gap or cushion? and is the gap number even one we could have BET?
# ---------------------------------------------------------------------------------------------
# The headline (+13.7% on |gap|>=1) was computed with `sharp_at(..., 0)` - the LAST Pinnacle line
# before tip. That is the sharp CLOSE. It is not knowable when we bet, and this project has been
# burned by exactly that once already: ping_vs_open.py judged a gate at the opening line and
# priced at the ping, and the resulting "+4.0%" was pure construction. So the first job here is
# to rebuild the whole thing at horizons we could actually act on.
#
# The 12h/6h split from gap_final is the specific worry:
#     sharp as of 12h before tip, |gap|>=1  ->  n=64   -14.9%
#     sharp as of  6h before tip, |gap|>=1  ->  n=105  +13.0%
# Two explanations, opposite implications:
#   TIMING     Pinnacle's early prop lines are low-limit and genuinely uninformative; the edge
#              only exists once real money arrives. Then the rule works but must be run late.
#   COMPOSITION 64 and 105 are different bet sets. The gap may be fine at both horizons and the
#              difference is just which quotes happen to have an early sharp line.
# Only a CONSTANT SET separates them: quotes carrying a sharp line at EVERY horizon, repriced at
# each one. If the curve slopes on a frozen set, it is timing. If it is flat, it was composition.
#
# Then the question actually asked: gap or cushion? Same rows, same prices, three ways -
# gap alone, cushion alone, and each inside the other's blind spot.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260821)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
HORIZ = [24, 12, 9, 6, 3, 1]
gof, dateof = {}, {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    gof[(hm, t2)] = gid; gof[(aw, t2)] = gid; dateof[t2] = d2

pin = collections.defaultdict(list)
for r in load("pinn_snapshots.csv"):
    cap, ln = ts(r.get("captured_utc")), f(r.get("pinn_line"))
    pl, mk = (r.get("player") or "").lower(), r.get("market")
    if cap and ln is not None and pl and mk: pin[(pl, mk)].append((cap, ln))
for r in load("bets_log.csv"):
    cap, ln = ts(r.get("captured_utc")), f(r.get("pinn"))
    pl, mk = (r.get("player") or "").lower(), r.get("market")
    if cap and ln is not None and pl and mk: pin[(pl, mk)].append((cap, ln))
for v in pin.values(): v.sort()
def sharp_at(pl, mk, gt, hours):
    cut = gt - datetime.timedelta(hours=hours)
    got = [x for x in pin.get((pl, mk), []) if x[0] <= cut and (gt-x[0]).total_seconds() < 30*3600]
    return got[-1][1] if got else None
_mc = {}
def med_team(pl, mk, gt):
    k = (pl, mk, gt)
    if k in _mc: return _mc[k]
    g = [r for r in hist.get(pl, []) if r["tip"] < gt]
    out = None
    if g:
        cur = g[-1]["tm"]; g2 = [r for r in g if r["tm"] == cur]
        if len(g2) >= 5: out = statistics.median([r[mk] for r in g2[-10:]])
    _mc[k] = out
    return out

Q = []
for (pl, mk, gt), sdq in side.items():
    if "Over" not in sdq or "Under" not in sdq: continue
    if abs(sdq["Over"][1] - sdq["Under"][1]) > 0.01: continue
    now = pgrow.get((pl, gt)); tm = teamof.get(pl)
    if not now or mk not in now or not tm: continue
    ln = sdq["Over"][1]
    if now[mk] == ln: continue
    md = med_team(pl, mk, gt)
    sp = {h: sharp_at(pl, mk, gt, h) for h in HORIZ}
    Q.append(dict(pl=pl, mk=mk, gt=gt, gid=gof[(tm, gt)], date=dateof.get(gt, ""),
                  ln=ln, o_od=sdq["Over"][2], u_od=sdq["Under"][2],
                  o_won=now[mk] > ln, u_won=now[mk] < ln,
                  cush=(md-ln) if md is not None else None, sp=sp))
def ret(r, sd): return ((r[sd+"_od"]-1) if r[sd+"_won"] else -1.0)
def gap_rows(h, thr=1.0):
    """the bets |gap|>=thr would place using the sharp line as of h hours before tip"""
    out = []
    for r in Q:
        s = r["sp"].get(h)
        if s is None: continue
        g = s - r["ln"]
        if abs(g) < thr: continue
        sd = "o" if g > 0 else "u"
        out.append((r, sd, g))
    return out
def sc(rows):
    if not rows: return 0, 0.0, 0.0
    n = len(rows)
    w = sum(1 for r, sd, _ in rows if r[sd+"_won"])
    u = sum(ret(r, sd) for r, sd, _ in rows)
    return n, 100*w/n, 100*u/n
def pboot(rows, T=2500):
    bp = collections.defaultdict(list)
    for r, sd, g in rows: bp[r["pl"]].append((r, sd, g))
    k = list(bp); o = []
    for _ in range(T):
        s = [x for p in [random.choice(k) for _ in k] for x in bp[p]]
        o.append(100*sum(ret(r, sd) for r, sd, _ in s)/len(s))
    o.sort(); return o[int(T*.025)], o[int(T*.975)]

print("="*104)
print("  1. REALISTIC - what |gap|>=1 would have returned, run at each horizon")
print("="*104)
print(f"  {'sharp known':<16}{'n':>6}{'hit%':>8}{'ROI':>9}   95% CI (player-block)")
byh = {}
for h in HORIZ:
    rows = gap_rows(h); byh[h] = rows
    if len(rows) < 30: print(f"  {h:>3}h before tip   n={len(rows)} too few"); continue
    n, w, v = sc(rows); lo, hi = pboot(rows)
    print(f"  {h:>3}h before tip {n:>6}{w:>7.1f}%{v:>+8.1f}%   [{lo:+6.1f},{hi:+6.1f}]")
print("")
keys = None
for h in HORIZ:
    s = {(r["pl"], r["mk"], r["gt"]) for r, _, _ in byh.get(h, [])}
    keys = s if keys is None else (keys & s)
print("="*104)
print(f"  2. CONSTANT SET - the same {len(keys)} bets repriced at every horizon. Slope here = TIMING.")
print("="*104)
if len(keys) >= 25:
    for h in HORIZ:
        rows = [(r, sd, g) for r, sd, g in byh.get(h, []) if (r["pl"], r["mk"], r["gt"]) in keys]
        if len(rows) < 20: print(f"  {h:>3}h  n={len(rows)} too few"); continue
        n, w, v = sc(rows)
        flips = sum(1 for r, sd, g in rows
                    if any(sd != ("o" if (r["sp"].get(h2) or 0) - r["ln"] > 0 else "u")
                           for h2 in HORIZ if r["sp"].get(h2) is not None))
        print(f"  {h:>3}h before tip {n:>6}{w:>7.1f}%{v:>+8.1f}%     side changed vs another horizon on {flips}")
else:
    print(f"  only {len(keys)} quotes carry a sharp line at all {len(HORIZ)} horizons - cannot")
    print("  freeze the set. That itself is the answer: early sharp coverage is too thin to")
    print("  distinguish timing from composition, so the 12h number rests on different bets.")
print("")
print("="*104)
print("  3. GAP or CUSHION? - identical rows, actionable 6h sharp line")
print("="*104)
H = 6
base = [(r, sd, g) for r, sd, g in gap_rows(H) if r["cush"] is not None]
allc = [r for r in Q if r["cush"] is not None and r["sp"].get(H) is not None]
def ov(rows): return (len(rows), 100*sum(1 for r in rows if r["o_won"])/len(rows),
                      100*sum(ret(r, "o") for r in rows)/len(rows)) if rows else (0, 0, 0)
n, w, v = sc(base); print(f"    gap>=1 toward sharp                  n={n:<5}{w:>6.1f}%{v:>+8.1f}%")
d = [r for r in allc if r["cush"] >= 3]
n2, w2, v2 = ov(d);   print(f"    cushion>=3 -> OVER (overshoot rule)   n={n2:<5}{w2:>6.1f}%{v2:>+8.1f}%")
bo = [(r, sd, g) for r, sd, g in base if r["cush"] >= 3]
n3, w3, v3 = sc(bo);  print(f"    both                                 n={n3:<5}{w3:>6.1f}%{v3:>+8.1f}%")
go = [(r, sd, g) for r, sd, g in base if r["cush"] < 3]
n4, w4, v4 = sc(go);  print(f"    gap only, cushion<3                  n={n4:<5}{w4:>6.1f}%{v4:>+8.1f}%")
co = [r for r in d if abs((r["sp"][H] or r["ln"]) - r["ln"]) < 1.0]
n5, w5, v5 = ov(co);  print(f"    cushion only, gap<1                  n={n5:<5}{w5:>6.1f}%{v5:>+8.1f}%")
print("")
print("="*104)
print("  4. OUT OF SAMPLE on the actionable version")
print("="*104)
dts = sorted({r["date"] for r, _, _ in base}); cut = dts[len(dts)//2] if dts else ""
for lbl, sel in ((f"first half (< {cut})", lambda d_: d_ < cut), ("second half", lambda d_: d_ >= cut)):
    rows = [(r, sd, g) for r, sd, g in base if sel(r["date"])]
    if len(rows) < 20: print(f"    {lbl:<26} n={len(rows)} too few"); continue
    n, w, v = sc(rows); print(f"    {lbl:<26} n={n:<5}{w:>6.1f}%{v:>+8.1f}%")
print("")
print("="*104)
print("  5. THE NULL on the actionable version")
print("="*104)
if len(base) >= 40:
    real = sc(base)[2]
    pool = [r for r in Q if r["sp"].get(H) is not None]
    beat = 0; T = 4000
    for _ in range(T):
        samp = random.sample(pool, min(len(base), len(pool)))
        sds = [sd for _, sd, _ in base]
        v = 100*sum(ret(r, sds[i % len(sds)]) for i, r in enumerate(samp))/len(samp)
        if v >= real: beat += 1
    print(f"    {len(base)} bets at {real:+.1f}% vs random quotes from the same sharp-covered pool,")
    print(f"    same side mix: p = {beat/T:.4f}")
print("")
print("="*104)
print("  6. VERDICT INPUTS")
print("="*104)
sl = len({r["date"] for r in Q if r["sp"].get(H) is not None})
print(f"    slates with any 6h sharp coverage: {sl}")
print(f"    gap bets per covered slate       : {len(base)/max(sl,1):.2f}")
print(f"    cushion>=3 bets per covered slate: {len(d)/max(sl,1):.2f}")
