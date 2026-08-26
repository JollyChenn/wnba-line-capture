# Confound + mechanism audit for the WITHIN-GAME TIMING dimension.
#  C1  is quarter-concentration just 1/volume?  (HHI is mechanically higher for low scorers)
#  C2  residual (actual - line) vs each timing feature, player-block permutation
#  C3  does the qconc over/under gradient survive stratifying on LINE LEVEL (volume)?
import csv, os, sys, math, random, statistics, datetime, collections, json
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])

R = json.load(open(os.path.join(D, "tim_rows.json")))
SCOR = ("pts", "pra", "pr", "pa"); NONS = ("reb", "ast", "ra")
byp = collections.defaultdict(list)
for r in R: byp[r["pl"]].append(r)
for v in byp.values(): v.sort(key=lambda x: x["gt"])
FEAT0 = {p: dict(h1share=v[0]["h1share"], q4share=v[0]["q4share"], qconc=v[0]["qconc"],
                 q4app=v[0]["q4app"], cv=v[0]["cv"]) for p, v in byp.items()}
for r in R: r.update(FEAT0[r["pl"]])

# player volume/role
vol = {}
for p in FEAT0:
    g = [x for (pl, tp), x in pgrow.items() if pl == p]
    if not g: continue
    vol[p] = dict(mpts=statistics.mean(x["pts"] for x in g), mmin=statistics.mean(x["min"] for x in g),
                  muse=statistics.mean(x["use"] for x in g))

def rankv(a):
    n = len(a); d = [0.0] * n
    order = sorted(range(n), key=lambda i: a[i]); i = 0
    while i < n:
        j = i
        while j + 1 < n and a[order[j + 1]] == a[order[i]]: j += 1
        rk = (i + j) / 2 + 1
        for k in range(i, j + 1): d[order[k]] = rk
        i = j + 1
    return d
def sprho(u, v):
    ru, rv = rankv(u), rankv(v); n = len(u); mu = (n + 1) / 2
    su = math.sqrt(sum((x - mu) ** 2 for x in ru)); sv = math.sqrt(sum((x - mu) ** 2 for x in rv))
    if su == 0 or sv == 0: return 0.0
    return sum((a - mu) * (b - mu) for a, b in zip(ru, rv)) / (su * sv)

print("C1  player-level correlations (n=%d players)" % len(vol))
ps = sorted(vol)
for k in ("qconc", "q4app", "h1share", "q4share", "cv"):
    a = [FEAT0[p][k] for p in ps]
    print("   %-8s vs mean pts %+0.3f   vs mean min %+0.3f   vs usage %+0.3f   vs cv %+0.3f" % (
        k, sprho(a, [vol[p]["mpts"] for p in ps]), sprho(a, [vol[p]["mmin"] for p in ps]),
        sprho(a, [vol[p]["muse"] for p in ps]), sprho(a, [FEAT0[p]["cv"] for p in ps])))

# C2  residual vs feature, player-block permutation via a linear-in-feature statistic
print("\nC2  residual (actual - line) vs timing feature, player-block permutation (10k)")
def block_perm(rows, key, nperm=10000):
    v = rankv([r["resid"] for r in rows]); n = len(v); mu = (n + 1) / 2
    vc = [x - mu for x in v]
    S = collections.defaultdict(float); N = collections.Counter()
    for r, c in zip(rows, vc): S[r["pl"]] += c; N[r["pl"]] += 1
    pls = sorted(S)
    obs = sum(FEAT0[p][key] * S[p] for p in pls)
    # normalise to a rho-like scale for reporting
    fv = [FEAT0[p][key] for p in pls]
    donors = list(pls); cnt = 0; dist = []
    for _ in range(nperm):
        random.shuffle(donors)
        t = sum(FEAT0[d][key] * S[p] for p, d in zip(pls, donors))
        dist.append(t)
        if abs(t - statistics.mean([0])) >= abs(obs): pass
    m = statistics.mean(dist); sd = statistics.pstdev(dist)
    cnt = sum(1 for t in dist if abs(t - m) >= abs(obs - m))
    z = (obs - m) / sd if sd > 0 else 0.0
    rho = sprho([r[key] for r in rows], [r["resid"] for r in rows])
    return rho, z, (cnt + 1) / (nperm + 1)
for grp, name in ((SCOR, "scoring"), (NONS, "non-scor")):
    rows = [r for r in R if r["mk"] in grp]
    for k in ("h1share", "q4share", "qconc", "q4app"):
        rho, z, p = block_perm(rows, k, 8000)
        print("   %-9s %-8s rho %+0.4f  z %+0.2f  p(player-block) %.3f  n %d" % (name, k, rho, z, p, len(rows)))

# C3  qconc gradient stratified on LINE LEVEL (volume proxy) - scoring markets
print("\nC3  qconc OVER gradient inside line-level tertiles, scoring markets")
rows = [r for r in R if r["mk"] in SCOR]
for mk in ("pts", "pra", "pr", "pa"):
    sub = [r for r in rows if r["mk"] == mk]
    lv = sorted(r["line"] for r in sub); l1, l2 = lv[len(lv)//3], lv[2*len(lv)//3]
    for tl, tf in (("lineLO", lambda r: r["line"] < l1), ("lineMD", lambda r: l1 <= r["line"] < l2), ("lineHI", lambda r: r["line"] >= l2)):
        s2 = [r for r in sub if tf(r)]
        if len(s2) < 100: continue
        qm = statistics.median(r["qconc"] for r in s2)
        out = []
        for ql, qf in (("concHI", lambda r: r["qconc"] >= qm), ("concLO", lambda r: r["qconc"] < qm)):
            g = [r for r in s2 if qf(r)]
            roi = sum((r["over_od"] - 1) if r["over_won"] else -1.0 for r in g) / len(g)
            out.append("%s n=%d over%%=%.1f ROI %+0.1f%%" % (ql, len(g), 100*sum(1 for r in g if r["over_won"])/len(g), 100*roi))
        print("   %-4s %-7s  %s | %s" % (mk, tl, out[0], out[1]))
print("\ndone")
