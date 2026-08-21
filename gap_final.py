# gap_final.py - is sharp-divergence its own edge, or the overshoot signal re-measured?
# ---------------------------------------------------------------------------------------------
# gap_combo: toward-sharp return rises with |gap| (rho +0.2503, player-permutation p = 0.0083),
# both directions pay nearly identically (+13.6% over / +12.4% under), and it holds out of sample
# (+14.5% / +11.4%). That is the cleanest profile anything has shown this season.
#
# But corr(|gap|, cushion) = +0.268, and cushion IS the overshoot rule. If a big sharp gap simply
# means "1xbet's line is far from her median", this is not a new edge, it is the old one measured
# through a different instrument. Three tests decide it:
#
#  1 STRATIFY. Split by cushion, then look at gap INSIDE each stratum. If gap only separates in
#    the deep-cushion half, it is the same information. If it separates in BOTH, it is its own.
#  2 THE DIRECT COMPARISON. On the identical rows, what does cushion alone earn, what does gap
#    alone earn, and what do they earn together? boardhunt put cushion-3+ at +5.4% board-wide.
#  3 THE ARTIFACT. In gap_combo, quotes with gap exactly 0 defaulted to the UNDER side because
#    "toward sharp" is undefined there, and that cell read -20.0%. That is a coding default, not
#    a finding, and it must not be feeding the dose-response. Re-check with gap=0 handled honestly.
#
# Plus the practical question: at |gap|>=1 how many bets per slate does this actually produce,
# and is the sharp line knowable EARLY enough to act on?
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260821)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
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
    """sharp line as of `hours` before tip - lets us ask how early this is knowable"""
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
    sp = sharp_at(pl, mk, gt, 0)
    if sp is None: continue
    md = med_team(pl, mk, gt)
    if md is None: continue
    gap = sp - ln
    Q.append(dict(pl=pl, mk=mk, gt=gt, gid=gof[(tm, gt)], date=dateof.get(gt, ""), mkt=mk,
                  ln=ln, gap=gap, cush=md-ln, o_od=sdq["Over"][2], u_od=sdq["Under"][2],
                  o_won=now[mk] > ln, u_won=now[mk] < ln,
                  sp6=sharp_at(pl, mk, gt, 6), sp12=sharp_at(pl, mk, gt, 12)))
def side_ret(r, sd): return ((r[sd+"_od"]-1) if r[sd+"_won"] else -1.0)
def toward(r):
    if abs(r["gap"]) < 0.01: return None
    return "o" if r["gap"] > 0 else "u"
def roi(rows): return 100*statistics.mean([side_ret(r, toward(r)) for r in rows]) if rows else 0
def hitr(rows): return 100*sum(1 for r in rows if r[toward(r)+"_won"])/len(rows) if rows else 0
def pboot(rows, T=2500):
    bp = collections.defaultdict(list)
    for r in rows: bp[r["pl"]].append(r)
    k = list(bp); o = []
    for _ in range(T): o.append(roi([x for p in [random.choice(k) for _ in k] for x in bp[p]]))
    o.sort(); return o[int(T*.025)], o[int(T*.975)]
def show(rows, lbl, minn=30):
    if len(rows) < minn: print(f"    {lbl:<52} n={len(rows)} too few"); return
    lo, hi = pboot(rows)
    star = "  <<<" if lo > 0 else ""
    print(f"    {lbl:<52} n={len(rows):<5}{hitr(rows):>6.1f}%{roi(rows):>+8.1f}%  [{lo:+6.1f},{hi:+6.1f}]{star}")
DIS = [r for r in Q if toward(r)]
print(f"{len(Q)} quotes with a sharp line and a team-filtered median; "
      f"{len(DIS)} are genuine disagreements (gap != 0)")
print(f"  markets: " + ", ".join(f"{k}:{v}" for k, v in collections.Counter(r['mkt'] for r in DIS).most_common()))
print("")
print("="*104)
print("  1. STRATIFY BY CUSHION - does the gap still separate inside each half?")
print("="*104)
cm = statistics.median(r["cush"] for r in DIS)
print(f"  cushion median {cm:+.1f}")
for clab, csel in ((f"cushion SMALL (<= {cm:+.1f})", lambda r: r["cush"] <= cm),
                   (f"cushion BIG  (>  {cm:+.1f})", lambda r: r["cush"] > cm)):
    print(f"  {clab}")
    show([r for r in DIS if csel(r) and abs(r["gap"]) >= 1.0], "    gap >= 1.0  (big disagreement)", minn=20)
    show([r for r in DIS if csel(r) and abs(r["gap"]) < 1.0],  "    gap <  1.0  (small)", minn=20)
print("")
print("  if the gap separates in BOTH halves it carries information cushion does not.")
print("")
print("="*104)
print("  2. HEAD TO HEAD on the same rows: cushion alone vs gap alone")
print("="*104)
BIG = [r for r in DIS if abs(r["gap"]) >= 1.0]
DEEP = [r for r in DIS if r["cush"] >= 3]
print(f"    bet toward sharp when |gap|>=1        n={len(BIG):<5} ROI {roi(BIG):+6.1f}%")
ov = lambda rows: 100*statistics.mean([side_ret(r, "o") for r in rows]) if rows else 0
print(f"    bet OVER when cushion>=3 (overshoot)  n={len(DEEP):<5} ROI {ov(DEEP):+6.1f}%")
both = [r for r in DIS if abs(r["gap"]) >= 1.0 and r["cush"] >= 3]
print(f"    both conditions                       n={len(both):<5} ROI {roi(both):+6.1f}%")
onlygap = [r for r in DIS if abs(r["gap"]) >= 1.0 and r["cush"] < 3]
print(f"    gap only, cushion < 3                 n={len(onlygap):<5} ROI {roi(onlygap):+6.1f}%"
      f"   <- gap working WITHOUT overshoot")
print("")
print("="*104)
print("  3. THE gap=0 ARTIFACT - excluded from every number above")
print("="*104)
Z = [r for r in Q if abs(r["gap"]) < 0.01]
print(f"    books agree exactly: n={len(Z)}")
if Z:
    print(f"      betting the OVER on them  ROI {ov(Z):+6.1f}%")
    print(f"      betting the UNDER on them ROI "
          f"{100*statistics.mean([side_ret(r,'u') for r in Z]):+6.1f}%")
    print("      neither side is 'toward sharp' - the -20.0% in gap_combo was my default, not a")
    print("      finding. the dose-response test already excluded these rows.")
print("")
print("="*104)
print("  4. IS IT KNOWABLE EARLY? sharp line as of N hours before tip")
print("="*104)
for h, key in ((12, "sp12"), (6, "sp6")):
    g = [r for r in Q if r[key] is not None and abs(r[key]-r["ln"]) >= 1.0]
    if len(g) < 30: print(f"    {h}h out: n={len(g)} too few"); continue
    tw = lambda r: "o" if (r[key]-r["ln"]) > 0 else "u"
    v = 100*statistics.mean([side_ret(r, tw(r)) for r in g])
    w = 100*sum(1 for r in g if r[tw(r)+"_won"])/len(g)
    print(f"    sharp known {h}h before tip, |gap|>=1: n={len(g):<5}{w:>6.1f}%{v:>+8.1f}%")
print("")
print("="*104)
print("  5. VOLUME")
print("="*104)
sl = len({r["date"] for r in Q})
print(f"    |gap|>=1 fired {len(BIG)} times over {sl} slates = {len(BIG)/sl:.2f} per slate")
print(f"    but sharp coverage reaches only {len(Q)} of the board's quotes, almost all pts.")
print(f"    widening pinn capture to reb/ast would unlock the combo markets (pr/pra/pa/ra).")
