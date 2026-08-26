# Final control: 77% of the claim's panel uses the trailing median ITSELF as the reference line,
# so the label is a deterministic function of the same quantity the outcome subtracts.
# The 457 real-posted-line rows have a partially independent reference. Test them separately,
# against the same artifact null.
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
    H1[(r["player"], gmeta[gid][1])] = dict(h1=f(r["h1"]), gid=gid)
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
    M.append(dict(pl=pl, gid=h["gid"], h1=h["h1"], pts=now["pts"], med=m_g, real=line is not None,
                  ref=(line if line is not None else m_g), npts=nx["pts"], resid=nx["pts"]-m_g))
EV = lambda r: r["h1"] > r["ref"]
def gp(vals, labs):
    a = [v for v, l in zip(vals, labs) if l]; b = [v for v, l in zip(vals, labs) if not l]
    return statistics.mean(a)-statistics.mean(b)

for nm, sub in [("MEDIAN-PROXY rows (label = h1 > med_G, fully coupled)", [r for r in M if not r["real"]]),
                ("REAL POSTED-LINE rows (reference partly independent)", [r for r in M if r["real"]])]:
    labs = [EV(r) for r in sub]
    obs = gp([r["resid"] for r in sub], labs)
    byp = collections.defaultdict(list)
    for i, r in enumerate(sub): byp[r["pl"]].append(i)
    s = []
    for _ in range(4000):
        nv = [0.0]*len(sub)
        for p_, ii in byp.items():
            v = [sub[i]["npts"] for i in ii]; random.shuffle(v)
            for i, x in zip(ii, v): nv[i] = x
        s.append(gp([nv[i]-sub[i]["med"] for i in range(len(sub))], labs))
    s.sort()
    print("%s\n   n=%d ev=%d  observed %+.3f | artifact-null mean %+.3f p95 %+.3f -> percentile %.0f, p=%.3f" % (
        nm, len(sub), sum(labs), obs, statistics.mean(s), s[int(.95*len(s))],
        100.0*sum(1 for x in s if x < obs)/len(s), (sum(1 for x in s if x >= obs)+1)/(len(s)+1)))
