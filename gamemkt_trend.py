# gamemkt_trend.py - the totals/spread pattern is ORDERED, so test the trend, not the cells.
# ---------------------------------------------------------------------------------------------
# gamemkt.py showed a beautifully symmetric ladder:
#     overs  by total:  -13.2 / -6.9 / +1.2      unders by total:  -1.0 / -7.3 / -15.1
#     overs  by spread: -6.5 / +4.8 / -19.1      unders by spread: -7.5 / -18.2 / +4.1
# Cells against a max-cell ceiling are the wrong test for this - the evidence IS the ordering.
# Correct null: spearman of (game feature) vs (per-quote over return), permuting the FEATURE
# across games, outcomes untouched. Also: partial independence - spread-wide and total-low games
# overlap; does each feature matter with the other held fixed?
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260821)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
ALLMK = ("pts", "pr", "pra", "pa", "ra", "reb", "ast")
gof, oppof = {}, {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    gof[(hm, t2)] = gid; gof[(aw, t2)] = gid; oppof[(hm, t2)] = aw; oppof[(aw, t2)] = hm
GL = collections.defaultdict(dict)
for r in load("gamelines.csv"):
    st = (r.get("start") or "")[:10].replace("-", "")
    tm = (r.get("teams") or "").split("|")
    if len(tm) != 2: continue
    ab = tuple(sorted(FULL.get(t.strip(), "") for t in tm))
    if "" in ab: continue
    cap, pts = ts(r.get("captured_utc")), f(r.get("points"))
    if not cap: continue
    s = GL[(st, ab)]
    if r.get("type") == "total" and pts is not None and ("tot" not in s or cap > s["tot"][0]):
        s["tot"] = (cap, pts)
    if r.get("type") == "spread" and pts is not None and ("spr" not in s or cap > s["spr"][0]):
        s["spr"] = (cap, abs(pts))
Q = []
for (pl, mk, gt), sdq in side.items():
    if mk not in ALLMK or "Over" not in sdq or "Under" not in sdq: continue
    if abs(sdq["Over"][1] - sdq["Under"][1]) > 0.01: continue
    now = pgrow.get((pl, gt)); tm = teamof.get(pl)
    if not now or mk not in now or not tm: continue
    ln = sdq["Over"][1]
    if now[mk] == ln: continue
    gid = gof[(tm, gt)]; d2, t2, hm, aw = gmeta[gid]
    s = GL.get((d2, tuple(sorted((hm, aw)))), {})
    tot = s.get("tot", (None, None))[1]; spr = s.get("spr", (None, None))[1]
    if tot is None or spr is None: continue
    Q.append(dict(gid=gid, tot=tot, spr=spr,
                  ret=((sdq["Over"][2]-1) if now[mk] > ln else -1.0)))
print(f"{len(Q)} quotes with BOTH total and spread, {len({r['gid'] for r in Q})} games")

def spearman(xs, ys):
    def rk(v):
        s = sorted(range(len(v)), key=lambda i: v[i]); r = [0]*len(v)
        for i, j in enumerate(s): r[j] = i
        return r
    a, b = rk(xs), rk(ys); ma, mb = statistics.mean(a), statistics.mean(b)
    num = sum((a[i]-ma)*(b[i]-mb) for i in range(len(a)))
    den = math.sqrt(sum((x-ma)**2 for x in a)*sum((y-mb)**2 for y in b))
    return num/den if den else 0.0

bg = collections.defaultdict(list)
for r in Q: bg[r["gid"]].append(r)
gk = list(bg)
gtot = {g: bg[g][0]["tot"] for g in gk}
gspr = {g: bg[g][0]["spr"] for g in gk}

for feat, gmap, expect in (("TOTAL", gtot, "positive rho: higher total, better overs"),
                           ("SPREAD", gmap := gspr, "negative rho: wider spread, worse overs")):
    real = spearman([gmap[r["gid"]] for r in Q], [r["ret"] for r in Q])
    vals = [gmap[g] for g in gk]
    beat = 0; T = 4000
    for _ in range(T):
        random.shuffle(vals)
        lab = dict(zip(gk, vals))
        rho = spearman([lab[r["gid"]] for r in Q], [r["ret"] for r in Q])
        if (rho >= real if real >= 0 else rho <= real): beat += 1
    print(f"  {feat:<7} vs over-return: rho = {real:+.4f}   game-permutation p = {beat/T:.4f}   ({expect})")

# partials: within total-terciles, does spread still order? and vice versa
def roi(rows): return 100*sum(r["ret"] for r in rows)/len(rows) if rows else 0
vt = sorted(gtot.values()); t1, t2_ = vt[len(vt)//3], vt[2*len(vt)//3]
vs = sorted(gspr.values()); s1, s2_ = vs[len(vs)//3], vs[2*len(vs)//3]
print("")
print("  SPREAD effect holding TOTAL fixed (over ROI, tight/mid/wide):")
for nm, sel in (("total low ", lambda g: gtot[g] <= t1), ("total mid ", lambda g: t1 < gtot[g] <= t2_),
                ("total high", lambda g: gtot[g] > t2_)):
    cells = []
    for nm2, sel2 in (("tight", lambda g: gspr[g] <= s1), ("mid", lambda g: s1 < gspr[g] <= s2_),
                      ("wide", lambda g: gspr[g] > s2_)):
        rows = [r for r in Q if sel(r["gid"]) and sel2(r["gid"])]
        cells.append(f"{nm2} {('n=%d %+.1f%%' % (len(rows), roi(rows))) if len(rows) >= 60 else 'n=%d few' % len(rows)}")
    print(f"    {nm}:  " + "   ".join(cells))
