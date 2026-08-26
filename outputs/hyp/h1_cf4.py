# Addendum: exact percentile of the observed gap inside the artifact null, a second null form
# that uses the EXACT observed next-game values, and a game-block bootstrap CI.
import os, sys, math, random, statistics, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hlib; ROOT = hlib.boot(globals())
random.seed(20260826)

H1 = {}
for r in load("outputs/hyp/h1_all.csv"):
    gid = r["game_id"]
    if gid not in gmeta: continue
    H1[(r["player"], gmeta[gid][1])] = dict(h1=f(r["h1"]), pts=f(r["pts"]), gid=gid)
Q = {}
for (pl, mk, gt), sd in side.items():
    if mk != "pts" or "Over" not in sd or "Under" not in sd: continue
    if sd["Over"][1] != sd["Under"][1]: continue
    Q[(pl, gt)] = sd["Over"][1]

M = []
for (pl, gt), h in sorted(H1.items()):
    now = pgrow.get((pl, gt))
    if not now or now["min"] < 8: continue
    p = [x for x in hist.get(pl, []) if x["tip"] < gt and x["tm"] == teamof.get(pl)][-10:]
    if len(p) < 5: continue
    m_g = statistics.median(x["pts"] for x in p)
    fut = [x for x in hist.get(pl, []) if x["tip"] > gt]
    if not fut: continue
    nx = fut[0]
    if nx["min"] < 8: continue
    line = Q.get((pl, gt))
    M.append(dict(pl=pl, gt=gt, gid=h["gid"], h1=h["h1"], pts=now["pts"], med=m_g,
                  ref=(line if line is not None else m_g), npts=nx["pts"], resid=nx["pts"]-m_g))
EV = lambda r: r["h1"] > r["ref"]
def gap(vals, labs):
    a = [v for v, l in zip(vals, labs) if l]; b = [v for v, l in zip(vals, labs) if not l]
    return statistics.mean(a) - statistics.mean(b)
labs = [EV(r) for r in M]
obs = gap([r["resid"] for r in M], labs)
print("panel n=%d  events=%d  observed gap %+.3f" % (len(M), sum(labs), obs))

byp = collections.defaultdict(list)
for i, r in enumerate(M): byp[r["pl"]].append(i)

# NULL A: resample next-game pts i.i.d. from the player's own season pool
pool = {p_: [x["pts"] for x in hist.get(p_, [])] for p_ in byp}
# NULL B: permute the OBSERVED next-game values within player (exact marginal preserved)
def run(kind, B=4000):
    out = []
    for _ in range(B):
        nv = [0.0]*len(M)
        for p_, ii in byp.items():
            if kind == "A":
                for i in ii: nv[i] = random.choice(pool[p_])
            else:
                v = [M[i]["npts"] for i in ii]; random.shuffle(v)
                for i, x in zip(ii, v): nv[i] = x
        out.append(gap([nv[i]-M[i]["med"] for i in range(len(M))], labs))
    out.sort(); return out
for kind, nm in [("A", "NULL A  i.i.d. resample from player's season pool"),
                 ("B", "NULL B  within-player shuffle of the OBSERVED next-game values")]:
    s = run(kind)
    pct = 100.0*sum(1 for x in s if x < obs)/len(s)
    print("%s\n   null mean %+.3f  p50 %+.3f  p95 %+.3f  |  observed %+.3f sits at the %.0fth percentile"
          "  (one-sided p vs artifact null = %.3f)" % (
          nm, statistics.mean(s), s[len(s)//2], s[int(.95*len(s))], obs, pct,
          (sum(1 for x in s if x >= obs)+1)/(len(s)+1)))

# game-block bootstrap CI on the observed gap (independent unit = game)
bygame = collections.defaultdict(list)
for r in M: bygame[r["gid"]].append(r)
gids = list(bygame)
bs = []
for _ in range(3000):
    rows = []
    for _ in range(len(gids)): rows += bygame[random.choice(gids)]
    l = [EV(r) for r in rows]
    if 5 <= sum(l) <= len(rows)-5: bs.append(gap([r["resid"] for r in rows], l))
bs.sort()
print("game-block bootstrap of observed gap: %+.3f  95%%CI [%+.3f,%+.3f]  (games=%d)" % (
      obs, bs[int(.025*len(bs))], bs[int(.975*len(bs))], len(gids)))
print("-> the artifact null's OWN mean (%+.3f) sits inside that CI." % statistics.mean(run("B", 800)))
