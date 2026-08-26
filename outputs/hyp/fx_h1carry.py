# ADVERSARIAL REBUILD: first-half carryover mechanism (h1 clears ref line in G -> next-game pts residual)
import os, sys, csv, math, random, statistics, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hlib; ROOT = hlib.boot(globals())
random.seed(20260826)

H1 = {}
for r in load("outputs/hyp/h1_all.csv"):
    gid = r["game_id"]
    if gid not in gmeta: continue
    H1[(r["player"], gmeta[gid][1])] = dict(h1=f(r["h1"]), h2=f(r["h2"]), pts=f(r["pts"]), gid=gid)
Q = {}
for (pl, mk, gt), sd in side.items():
    if mk != "pts" or "Over" not in sd or "Under" not in sd: continue
    if sd["Over"][1] != sd["Under"][1]: continue
    Q[(pl, gt)] = sd["Over"][1]

def trail(pl, gt, k=10, mk="pts"):
    p = [x for x in hist.get(pl, []) if x["tip"] < gt and x["tm"] == teamof.get(pl)][-k:]
    return statistics.median(x[mk] for x in p) if len(p) >= 5 else None

M = []
for (pl, gt), h in sorted(H1.items(), key=lambda k: (k[0][0], k[0][1])):
    now = pgrow.get((pl, gt))
    if not now or now["min"] < 8: continue
    m_g = trail(pl, gt)
    if m_g is None: continue
    fut = [x for x in hist.get(pl, []) if x["tip"] > gt]
    if not fut: continue
    nx = fut[0]
    if nx["min"] < 8: continue
    line = Q.get((pl, gt))
    ref = line if line is not None else m_g
    M.append(dict(pl=pl, gt=gt, gid=h["gid"], h1=h["h1"], pts=now["pts"], ref=ref,
                  real=(line is not None), med=m_g, npts=nx["pts"], nmin=nx["min"],
                  ngt=nx["tip"], resid=nx["pts"]-m_g, residg=now["pts"]-m_g))

# next-game game_id (for game-level blocking on the OUTCOME game)
tip2gid = {}
for g_, (dt, tp, ho, aw) in gmeta.items(): tip2gid.setdefault(tp, g_)
for r in M: r["ngid"] = tip2gid.get(r["ngt"], "T"+str(r["ngt"]))

ev = lambda r: r["h1"] > r["ref"]
A = [r for r in M if ev(r)]; Bn = [r for r in M if not ev(r)]
gap = statistics.mean(x["resid"] for x in A) - statistics.mean(x["resid"] for x in Bn)
print("PANEL n=%d players=%d  G-games=%d  Gplus1-games=%d  real-line rows=%d" %
      (len(M), len(set(r['pl'] for r in M)), len(set(r['gid'] for r in M)),
       len(set(r['ngid'] for r in M)), sum(1 for r in M if r['real'])))
print("event n=%d mean %+.3f | non n=%d mean %+.3f | GAP %+.3f" %
      (len(A), statistics.mean(x['resid'] for x in A), len(Bn), statistics.mean(x['resid'] for x in Bn), gap))
dd = sorted(set(gmeta[r['gid']][0] for r in M))
print("date range", dd[0], dd[-1])

def perm_p(rows, keyf, labf, valf, B=4000):
    by = collections.defaultdict(list)
    for i, r in enumerate(rows): by[keyf(r)].append(i)
    lab = [labf(r) for r in rows]; val = [valf(r) for r in rows]
    def g(l):
        a = [val[i] for i in range(len(l)) if l[i]]; b = [val[i] for i in range(len(l)) if not l[i]]
        return None if len(a) < 5 or len(b) < 5 else statistics.mean(a)-statistics.mean(b)
    obs = g(lab); c = 0
    for _ in range(B):
        l2 = list(lab)
        for k, ii in by.items():
            v = [lab[i] for i in ii]; random.shuffle(v)
            for i, x in zip(ii, v): l2[i] = x
        z = g(l2)
        if z is not None and abs(z) >= abs(obs): c += 1
    return obs, (c+1)/(B+1)

for nm, kf in [("player-block", lambda r: r["pl"]), ("G-game block", lambda r: r["gid"]),
               ("G+1-game block", lambda r: r["ngid"])]:
    o, p = perm_p(M, kf, ev, lambda r: r["resid"])
    print("perm p (%s): gap %+.3f  p=%.4f" % (nm, o, p))

# ---------- block bootstrap CI ----------
def boot_ci(rows, keyf, B=3000):
    by = collections.defaultdict(list)
    for r in rows: by[keyf(r)].append(r)
    ks = list(by); out = []
    for _ in range(B):
        s = []
        for _ in range(len(ks)): s.extend(by[random.choice(ks)])
        a = [x["resid"] for x in s if ev(x)]; b = [x["resid"] for x in s if not ev(x)]
        if len(a) >= 5 and len(b) >= 5: out.append(statistics.mean(a)-statistics.mean(b))
    out.sort(); n = len(out)
    return out[int(.025*n)], out[int(.975*n)], n
for nm, kf in [("player", lambda r: r["pl"]), ("G-game", lambda r: r["gid"]), ("G+1-game", lambda r: r["ngid"])]:
    lo, hi, nb = boot_ci(M, kf)
    print("block bootstrap CI (%s blocks): [%+.3f, %+.3f]" % (nm, lo, hi))

# ---------- drop top contributors ----------
def contrib(rows, unit):
    base = None
    a = [x["resid"] for x in rows if ev(x)]; b = [x["resid"] for x in rows if not ev(x)]
    base = statistics.mean(a)-statistics.mean(b)
    sc = {}
    for u in set(unit(r) for r in rows):
        s = [r for r in rows if unit(r) != u]
        a = [x["resid"] for x in s if ev(x)]; b = [x["resid"] for x in s if not ev(x)]
        if len(a) < 5 or len(b) < 5: continue
        sc[u] = base - (statistics.mean(a)-statistics.mean(b))
    return sorted(sc.items(), key=lambda kv: -kv[1])
for nm, uf in [("player", lambda r: r["pl"]), ("G-game", lambda r: r["gid"])]:
    c = contrib(M, uf)
    top = [u for u, _ in c[:2]]
    print("\ntop-2 %s contributors: %s" % (nm, [(u, round(v,3)) for u, v in c[:2]]))
    rest = [r for r in M if uf(r) not in top]
    a = [x["resid"] for x in rest if ev(x)]; b = [x["resid"] for x in rest if not ev(x)]
    g2 = statistics.mean(a)-statistics.mean(b)
    o, p = perm_p(rest, lambda r: r["pl"], ev, lambda r: r["resid"], B=3000)
    lo, hi, _ = boot_ci(rest, lambda r: r["pl"])
    print("  drop-top-2 %s: n=%d gap %+.3f  player-perm p=%.4f  CI[%+.3f,%+.3f]" % (nm, len(rest), g2, p, lo, hi))
