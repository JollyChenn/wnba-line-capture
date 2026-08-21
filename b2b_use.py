# b2b_use.py - can back-to-back actually be BET? and does the OPPONENT's rest matter too?
# ---------------------------------------------------------------------------------------------
# b2b_check.py found tired teams' overs at -25.9% / unders +11.6%, p=0.0447 at the team-night
# null, with the production check confirming the mechanism (actual-minus-median -0.30 on b2b vs
# +0.38 rested). Three things stand between that and a bet:
#
#  1 HOW OFTEN DOES IT FIRE? 9 team-nights all season. If it is one bet a fortnight it can never
#    be proven and barely matters. Rest is computed here from the TEAM schedule (gmeta), not from
#    a player's own game log, because a player who sat out breaks the player-level version.
#  2 WHICH MARKETS? reb/ast/ra died worst (-62%/-35%/-29%) and pts barely moved (-5.0%). That is
#    the fatigue signature - legs and hustle go before shooting - and it says bet the hustle
#    stats, not the scoring ones. Testing that split explicitly rather than eyeballing it.
#  3 THE OPPONENT'S REST - completely untested, and it is the more interesting half. If HER
#    opponent is on a back-to-back, she faces tired legs on defence. That should push her
#    production UP, not down. Same public schedule, opposite direction, and it fires just as
#    often. If both work, every back-to-back gives bets on BOTH teams.
#
# Nulls at the team-night level throughout, because that is where the label lives.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260821)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
ALLMK = ("pts", "pr", "pra", "pa", "ra", "reb", "ast")
HUSTLE = ("reb", "ast", "ra"); SCORE = ("pts", "pr", "pra", "pa")
gof, oppof, dateof = {}, {}, {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    gof[(hm, t2)] = gid; gof[(aw, t2)] = gid
    oppof[(hm, t2)] = aw; oppof[(aw, t2)] = hm; dateof[t2] = d2

# TEAM rest, from the schedule - independent of whether a given player suited up
def team_rest(tm, gt):
    ts_ = [t for t in tips_of.get(tm, []) if t < gt]
    return (gt - ts_[-1]).total_seconds()/86400 if ts_ else None
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
    if mk not in ALLMK or "Over" not in sdq or "Under" not in sdq: continue
    if abs(sdq["Over"][1] - sdq["Under"][1]) > 0.01: continue
    now = pgrow.get((pl, gt)); tm = teamof.get(pl)
    if not now or mk not in now or not tm: continue
    ln = sdq["Over"][1]
    if now[mk] == ln: continue
    op = oppof.get((tm, gt))
    mr, orr = team_rest(tm, gt), (team_rest(op, gt) if op else None)
    if mr is None or orr is None: continue
    md = med_team(pl, mk, gt)
    Q.append(dict(pl=pl, mk=mk, gt=gt, gid=gof[(tm, gt)], tm=tm, op=op, date=dateof.get(gt, ""),
                  ln=ln, o_od=sdq["Over"][2], u_od=sdq["Under"][2],
                  o_won=now[mk] > ln, u_won=now[mk] < ln, act=now[mk], med=md,
                  mine=(mr < 1.2), theirs=(orr < 1.2)))
def roi(rows, sd): return 100*sum((r[sd+'_od']-1) if r[sd+'_won'] else -1.0 for r in rows)/len(rows) if rows else 0
def hit(rows, sd): return 100*sum(1 for r in rows if r[sd+'_won'])/len(rows) if rows else 0
def tboot(rows, sd, T=2500):
    bt = collections.defaultdict(list)
    for r in rows: bt[(r["tm"], r["gt"])].append(r)
    k = list(bt); o = []
    for _ in range(T): o.append(roi([x for p in [random.choice(k) for _ in k] for x in bt[p]], sd))
    o.sort(); return o[int(T*.025)], o[int(T*.975)]
def show(rows, lbl, sd, minn=40):
    if len(rows) < minn: print(f"    {lbl:<50} n={len(rows)} too few"); return
    lo, hi = tboot(rows, sd)
    star = "  <<<" if lo > 0 else ""
    print(f"    {lbl:<50} n={len(rows):<5}{hit(rows,sd):>6.1f}%{roi(rows,sd):>+8.1f}%  [{lo:+6.1f},{hi:+6.1f}]{star}")

MINE = [r for r in Q if r["mine"]]; THEIRS = [r for r in Q if r["theirs"]]
BOTH = [r for r in Q if r["mine"] and r["theirs"]]
tn_m = {(r["tm"], r["gt"]) for r in MINE}; tn_t = {(r["tm"], r["gt"]) for r in THEIRS}
slates = len({r["date"] for r in Q})
print(f"{len(Q)} quotes over {slates} slates, team-rest resolved")
print(f"  HER team on a b2b   : {len(MINE)} quotes / {len(tn_m)} team-nights")
print(f"  OPPONENT on a b2b   : {len(THEIRS)} quotes / {len(tn_t)} team-nights")
print(f"  both tired          : {len(BOTH)} quotes")
print(f"  fire rate: {len(tn_m)/slates:.2f} tired team-nights per slate")
print("")
print("="*104)
print("  1. HER TEAM TIRED  vs  2. HER OPPONENT TIRED")
print("="*104)
show(MINE,   "  her team b2b: OVERS", "o")
show(MINE,   "  her team b2b: UNDERS", "u")
print("")
show(THEIRS, "  opponent b2b: OVERS", "o")
show(THEIRS, "  opponent b2b: UNDERS", "u")
print("")
show([r for r in Q if not r["mine"] and not r["theirs"]], "  both rested (control): OVERS", "o")
print("")
print("  production check - actual minus her median:")
for lbl, g in (("her team tired", MINE), ("opponent tired", THEIRS),
               ("both rested", [r for r in Q if not r["mine"] and not r["theirs"]])):
    v = [r["act"]-r["med"] for r in g if r["med"] is not None]
    if v: print(f"    {lbl:<20} {statistics.mean(v):+.2f}  (n={len(v)})")
print("")
print("="*104)
print("  3. WHICH MARKETS - fatigue should hit legs before shooting")
print("="*104)
for lbl, grp in (("HUSTLE (reb/ast/ra)", HUSTLE), ("SCORING (pts/pr/pra/pa)", SCORE)):
    print(f"  {lbl}")
    show([r for r in MINE if r["mk"] in grp], "    her team b2b: UNDERS", "u", minn=25)
    show([r for r in THEIRS if r["mk"] in grp], "    opponent b2b: OVERS", "o", minn=25)
print("")
print("="*104)
print("  4. TEAM-NIGHT NULLS")
print("="*104)
lab0 = {}
for r in Q: lab0.setdefault((r["tm"], r["gt"]), (r["mine"], r["theirs"]))
keys = list(lab0); vals = [lab0[k] for k in keys]
for nm, idx, pop, sd in (("her-team-tired UNDER", 0, MINE, "u"),
                         ("opponent-tired OVER", 1, THEIRS, "o")):
    real = roi(pop, sd); beat = 0; T = 4000; ok = 0
    for _ in range(T):
        random.shuffle(vals); lab = dict(zip(keys, vals))
        g = [r for r in Q if lab[(r["tm"], r["gt"])][idx]]
        if len(g) < 80: continue
        ok += 1
        if roi(g, sd) >= real: beat += 1
    print(f"  {nm:<26} real {real:+6.1f}%   team-night permutation p = {beat/max(ok,1):.4f}")
print("")
print("="*104)
print("  5. WHAT WOULD IT HAVE BET?  (hustle markets only, the strongest form)")
print("="*104)
rule = ([(r, "u") for r in MINE if r["mk"] in HUSTLE] +
        [(r, "o") for r in THEIRS if r["mk"] in HUSTLE])
if rule:
    n = len(rule)
    u = sum((r[sd+'_od']-1) if r[sd+'_won'] else -1.0 for r, sd in rule)
    w = sum(1 for r, sd in rule if r[sd+'_won'])
    print(f"    n={n}  {w}-{n-w}  {100*w/n:.1f}%  {u:+.2f}u  ROI {100*u/n:+.1f}%")
    print(f"    that is {n/slates:.2f} bets per slate across {slates} slates")
    dts = sorted({r["date"] for r, _ in rule}); cut = dts[len(dts)//2]
    for lbl, sel in (("first half", lambda d: d < cut), ("second half", lambda d: d >= cut)):
        g = [(r, sd) for r, sd in rule if sel(r["date"])]
        if len(g) < 20: continue
        uu = sum((r[sd+'_od']-1) if r[sd+'_won'] else -1.0 for r, sd in g)
        print(f"      {lbl:<12} n={len(g):<4} ROI {100*uu/len(g):+.1f}%")
