# shade.py - the whole-game shade. Rigorous pass on the one candidate that looks real.
# ---------------------------------------------------------------------------------------------
# fadehunt.py found that when the book shades the OPPONENT's player lines DOWN relative to their
# own medians, our overs run +37.1% (n=30, CI [+9.9,+62.7]), and the ordering is MONOTONIC:
#
#     opp lines shaded DOWN   +37.1%
#     opp lines neutral       +10.9%
#     opp lines shaded UP      -4.9%
#
# Two things make this different from everything else tried this season. First, monotonicity -
# gate 5, the tiers and the rank cells all failed exactly here. Second, there is a mechanism: our
# signal IS "the book cut this line too far". If the book is cutting the WHOLE GAME, there is more
# of the thing we are trying to buy. It is a dosage effect, and dosage effects are monotonic.
#
# But there is an obvious confound and it has to be killed first: if the whole game is shaded down
# then HER line is shaded down too, and her own cushion is already the core of the overshoot
# signal. If opp_shade is just her cushion wearing a disguise, it adds nothing. So:
#
#   1 TREND TEST, not max-cell. A monotonic feature is tested by correlating the feature with the
#     per-bet return, permuted at the GAME level. A max-single-cell ceiling is the wrong null for
#     an ordered feature - it is deliberately blind to the ordering that is the evidence.
#   2 CONFOUND. Correlate opp_shade with her own cushion. Then split her cushion into halves and
#     ask whether opp_shade still separates INSIDE each half.
#   3 Robustness: leave-one-team-out, leave-one-player-out, out-of-sample by date.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260819)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
SIGS = ("flip", "hotover", "overshoot"); BET_MKTS = ("pra", "pr", "pts")

tip_on, gof, oppof = {}, {}, {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    tip_on[(hm, d2)] = t2; tip_on[(aw, d2)] = t2
    gof[(hm, t2)] = gid; gof[(aw, t2)] = gid
    oppof[(hm, t2)] = aw; oppof[(aw, t2)] = hm
def med_before(pl, mk, gt):
    v = [r[mk] for r in hist.get(pl, []) if r["tip"] < gt]
    return statistics.median(v[-10:]) if len(v) >= 3 else None

shade = collections.defaultdict(list)
for (pl, mk, gt), sdq in side.items():
    if mk != "pts" or "Over" not in sdq: continue
    tm = teamof.get(pl)
    if not tm: continue
    m = med_before(pl, "pts", gt)
    if m is not None: shade[(tm, gt)].append((pl, sdq["Over"][1] - m))

S = []
for r in load("graded_bets.csv"):
    if (r.get("result") or "").upper() not in ("WIN", "LOSS"): continue
    src, mk, pl = (r.get("src") or ""), (r.get("market") or ""), (r.get("player") or "").lower()
    if src not in SIGS or mk not in BET_MKTS: continue
    tm = teamof.get(pl)
    gt = tip_on.get((tm, r.get("date") or "")) if tm else None
    if not gt: continue
    now = pgrow.get((pl, gt)); sdq = side.get((pl, mk, gt), {})
    if not now or "Over" not in sdq: continue
    _, ln, od = sdq["Over"]
    if now[mk] == ln: continue
    pv = prevline.get((pl, mk, gt))
    if pv is None or ln - pv >= 0.5: continue
    op = oppof.get((tm, gt))
    o_s = [v for _, v in shade.get((op, gt), [])]
    w_s = [v for p2, v in shade.get((tm, gt), []) if p2 != pl]
    md = med_before(pl, mk, gt)
    S.append(dict(pl=pl, mk=mk, gt=gt, gid=gof[(tm, gt)], date=r.get("date"), src=src, tm=tm,
                  ln=ln, od=od, won=now[mk] > ln,
                  ret=((od-1) if now[mk] > ln else -1.0),
                  cush=(md - ln) if md is not None else None,
                  opp=statistics.mean(o_s) if len(o_s) >= 3 else None,
                  own=statistics.mean(w_s) if len(w_s) >= 3 else None))
best = {}
for r in sorted(S, key=lambda x: -x["od"]): best.setdefault((r["pl"], r["gt"]), r)
S = sorted(best.values(), key=lambda r: r["date"])
for r in S:
    if r["opp"] is not None and r["own"] is not None: r["game"] = (r["opp"] + r["own"]) / 2
    else: r["game"] = None
A = [r for r in S if r["opp"] is not None and r["cush"] is not None]
print(f"MODEL S {len(S)} bets; {len(A)} have opponent shade AND her own cushion")
print("")

def roi(rows): return 100*sum(r["ret"] for r in rows)/len(rows) if rows else 0.0
def sc(rows):
    n = len(rows); w = sum(1 for r in rows if r["won"])
    return n, 100*w/n, sum(r["ret"] for r in rows), roi(rows)
def gboot(rows, T=3000):
    bg = collections.defaultdict(list)
    for r in rows: bg[r["gid"]].append(r)
    k = list(bg); o = []
    for _ in range(T):
        o.append(roi([x for p in [random.choice(k) for _ in k] for x in bg[p]]))
    o.sort(); return o[int(T*.025)], o[int(T*.975)]
def show(rows, lbl, minn=10):
    if len(rows) < minn: print(f"  {lbl:<46} n={len(rows)} too few"); return
    n, h, u, ro = sc(rows); lo, hi = gboot(rows)
    print(f"  {lbl:<46} n={n:<4}{h:>6.1f}%{u:>+8.2f}u{ro:>+8.1f}%  95CI [{lo:+6.1f},{hi:+6.1f}]")

def spearman(xs, ys):
    def rk(v):
        s = sorted(range(len(v)), key=lambda i: v[i]); r = [0]*len(v)
        for i, j in enumerate(s): r[j] = i
        return r
    a, b = rk(xs), rk(ys); n = len(xs)
    ma, mb = statistics.mean(a), statistics.mean(b)
    num = sum((a[i]-ma)*(b[i]-mb) for i in range(n))
    den = math.sqrt(sum((x-ma)**2 for x in a)*sum((y-mb)**2 for y in b))
    return num/den if den else 0.0

print("="*104)
print("  1. TREND TEST - the right null for an ordered feature")
print("="*104)
for feat in ("opp", "own", "game"):
    g = [r for r in S if r.get(feat) is not None]
    if len(g) < 30: continue
    rho = spearman([r[feat] for r in g], [r["ret"] for r in g])
    bg = collections.defaultdict(list)
    for r in g: bg[r["gid"]].append(r)
    gk = list(bg)
    beat = 0; T = 5000
    for _ in range(T):
        vals = [bg[k][0][feat] for k in gk]; random.shuffle(vals)
        xs, ys = [], []
        for k, v in zip(gk, vals):
            for r in bg[k]: xs.append(v); ys.append(r["ret"])
        if spearman(xs, ys) <= rho: beat += 1
    print(f"  {feat:<6} shade vs return   n={len(g):<4} spearman rho = {rho:+.3f}"
          f"   game-block permutation p = {beat/T:.4f}")
print("")
print("  negative rho = the more the book shades the game UP, the worse our over does.")
print("")
print("="*104)
print("  2. THE CONFOUND - is opponent shade just her own cushion again?")
print("="*104)
rho = spearman([r["opp"] for r in A], [r["cush"] for r in A])
print(f"  correlation between OPPONENT shade and HER OWN cushion: rho = {rho:+.3f}  (n={len(A)})")
print("  near zero means they are different information and the split below is not circular.")
print("")
cm = statistics.median(r["cush"] for r in A)
om = statistics.median(r["opp"] for r in A)
print(f"  splitting at her cushion median ({cm:+.1f}) and opponent-shade median ({om:+.2f}):")
for clab, csel in (("her cushion SMALL", lambda r: r["cush"] <= cm),
                   ("her cushion BIG",   lambda r: r["cush"] > cm)):
    for olab, osel in ((" + opp shaded DOWN", lambda r: r["opp"] <= om),
                       (" + opp shaded UP",   lambda r: r["opp"] > om)):
        show([r for r in A if csel(r) and osel(r)], "    " + clab + olab, minn=8)
    print("")
print("="*104)
print("  3. ROBUSTNESS of the shaded-down half")
print("="*104)
LO = [r for r in S if r.get("opp") is not None and r["opp"] <= om]
show(LO, "  opponent shaded DOWN (below median)")
show([r for r in S if r.get("opp") is not None and r["opp"] > om], "  opponent shaded UP")
print("")
bt = collections.Counter(r["tm"] for r in LO)
w = sorted((roi([r for r in LO if r["tm"] != t]), t) for t in bt)
print(f"  leave-one-TEAM-out : worst {w[0][0]:+.1f}% (drop {w[0][1]})   best {w[-1][0]:+.1f}%")
bp = collections.Counter(r["pl"] for r in LO)
wp = sorted((roi([r for r in LO if r["pl"] != p]), p) for p in bp)
print(f"  leave-one-PLAYER-out: worst {wp[0][0]:+.1f}% (drop {wp[0][1]})   best {wp[-1][0]:+.1f}%")
print(f"  {sum(1 for v, _ in wp if v <= 0)} of {len(wp)} single-player removals take it to zero or below")
dts = sorted({r["date"] for r in S}); cut = dts[int(len(dts)*0.6)]
show([r for r in LO if r["date"] < cut],  f"    first 60% of dates (< {cut})")
show([r for r in LO if r["date"] >= cut], f"    last 40% (>= {cut})")
print("")
print("="*104)
print("  4. WHAT IT WOULD HAVE DONE AS A GATE")
print("="*104)
show(S,  "  MODEL S as it stands")
show(LO, "  MODEL S + opponent shaded down (gate 6)")
print(f"  volume cost: {len(S)} bets -> {len(LO)} bets ({100*len(LO)/len(S):.0f}% kept)")
