# Mechanism-first tests for the WITHIN-GAME TIMING dimension.
#  M1  Are H1-heavy players really starters whose minutes get cut in blowouts?
#  M2  Do Q4-dependent players actually lose production in blowouts?
#  M3  Does quarter-concentration add anything BEYOND the known volatility (cv) gradient?
import csv, os, sys, math, random, statistics, datetime, collections, re, json
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])

R = json.load(open(os.path.join(D, "tim_rows.json")))
SCOR = ("pts", "pra", "pr", "pa"); NONS = ("reb", "ast", "ra")
marg = {}
for g in load("data/games_2026.csv"):
    hs, a_ = f(g.get("home_score")), f(g.get("away_score"))
    if hs is None or a_ is None: continue
    marg[(g.get("date"), g.get("home"))] = hs - a_
    marg[(g.get("date"), g.get("away"))] = a_ - hs

byp = collections.defaultdict(list)
for r in R: byp[r["pl"]].append(r)
for v in byp.values(): v.sort(key=lambda x: x["gt"])
FEAT0 = {p: dict(h1share=v[0]["h1share"], q4share=v[0]["q4share"], qconc=v[0]["qconc"],
                 q4app=v[0]["q4app"], cv=v[0]["cv"]) for p, v in byp.items()}
for r in R: r.update(FEAT0[r["pl"]])

# ---------- M1/M2 on RAW PRODUCTION, every player-game in the box (not just board rows) ----------
# use all 2026 player-games of players who have a timing profile
PG = []
for (pl, tp), row in pgrow.items():
    if pl not in FEAT0: continue
    m = marg.get((row["date"], row["tm"]))
    if m is None or row["min"] < 8: continue
    PG.append(dict(pl=pl, tm=row["tm"], tip=tp, date=row["date"], mn=row["min"], pts=row["pts"],
                   pra=row["pra"], absm=abs(m), win=m > 0, **FEAT0[pl]))
print("raw player-games with timing profile: %d  players %d" % (len(PG), len(set(x['pl'] for x in PG))))

med = {k: statistics.median(FEAT0[p][k] for p in FEAT0) for k in ("h1share", "q4share", "qconc", "q4app", "cv")}
print("player-level medians:", {k: round(v, 3) for k, v in med.items()})

def zscore_within_player(rows, key):
    """per-player z of `key` so blowout comparisons are not a player-mix artifact."""
    byp2 = collections.defaultdict(list)
    for r in rows: byp2[r["pl"]].append(r)
    out = []
    for p, v in byp2.items():
        if len(v) < 5: continue
        mu = statistics.mean(x[key] for x in v); sd = statistics.pstdev(x[key] for x in v)
        if sd <= 0: continue
        for x in v:
            y = dict(x); y["z"] = (x[key] - mu) / sd; out.append(y)
    return out

print("\nM1  MINUTES in blowouts vs close, split by h1share (within-player z of minutes)")
Z = zscore_within_player(PG, "mn")
for lab, fn in (("h1share HI", lambda r: r["h1share"] >= med["h1share"]),
                ("h1share LO", lambda r: r["h1share"] < med["h1share"])):
    for bl, bf in (("blowout>=15", lambda r: r["absm"] >= 15), ("close<8", lambda r: r["absm"] < 8)):
        g = [r for r in Z if fn(r) and bf(r)]
        print("   %-11s %-12s n=%-5d mean z(min) %+0.4f  mean min %.1f" % (
            lab, bl, len(g), statistics.mean(x["z"] for x in g), statistics.mean(x["mn"] for x in g)))
# direct: is minute-loss-in-blowout correlated with h1share, per player?
loss = {}
for p, v in collections.defaultdict(list, {k: [x for x in PG if x["pl"] == k] for k in set(x["pl"] for x in PG)}).items():
    bl = [x["mn"] for x in v if x["absm"] >= 15]; cl = [x["mn"] for x in v if x["absm"] < 8]
    if len(bl) >= 3 and len(cl) >= 3: loss[p] = statistics.mean(bl) - statistics.mean(cl)
def sprho(u, v):
    n = len(u); ru = {}; rv = {}
    for arr, d in ((u, ru), (v, rv)):
        order = sorted(range(n), key=lambda i: arr[i]); i = 0
        while i < n:
            j = i
            while j + 1 < n and arr[order[j + 1]] == arr[order[i]]: j += 1
            rk = (i + j) / 2 + 1
            for k in range(i, j + 1): d[order[k]] = rk
            i = j + 1
    mu = (n + 1) / 2
    su = math.sqrt(sum((ru[i] - mu) ** 2 for i in range(n))); sv = math.sqrt(sum((rv[i] - mu) ** 2 for i in range(n)))
    if su == 0 or sv == 0: return 0.0
    return sum((ru[i] - mu) * (rv[i] - mu) for i in range(n)) / (su * sv)
def perm_p(u, v, nperm=20000):
    obs = sprho(u, v); uu = list(u); c = 0
    for _ in range(nperm):
        random.shuffle(uu)
        if abs(sprho(uu, v)) >= abs(obs): c += 1
    return obs, (c + 1) / (nperm + 1)
ks = sorted(loss)
for k in ("h1share", "q4share", "q4app", "cv"):
    rho, p = perm_p([FEAT0[x][k] for x in ks], [loss[x] for x in ks], 5000)
    print("   per-player blowout minute-delta vs %-8s rho %+0.3f p %.3f (n players %d)" % (k, rho, p, len(ks)))

print("\nM2  PRODUCTION (within-player z of pts) in blowouts, split by q4share")
Z2 = zscore_within_player(PG, "pts")
for lab, fn in (("q4share HI", lambda r: r["q4share"] >= med["q4share"]),
                ("q4share LO", lambda r: r["q4share"] < med["q4share"])):
    for bl, bf in (("blowout>=15", lambda r: r["absm"] >= 15), ("close<8", lambda r: r["absm"] < 8)):
        g = [r for r in Z2 if fn(r) and bf(r)]
        print("   %-11s %-12s n=%-5d mean z(pts) %+0.4f" % (lab, bl, len(g), statistics.mean(x["z"] for x in g)))

# ---------- M3  concentration BEYOND cv: stratified over-rate / ROI ----------
print("\nM3  qconc effect WITHIN cv tertiles (the key control), board quotes")
cvv = sorted(FEAT0[p]["cv"] for p in FEAT0)
c1, c2 = cvv[len(cvv) // 3], cvv[2 * len(cvv) // 3]
for gname, grp in (("SCOR", SCOR), ("NONS", NONS)):
    rows = [r for r in R if r["mk"] in grp]
    for tl, tf in (("cvLO", lambda r: r["cv"] < c1), ("cvMD", lambda r: c1 <= r["cv"] < c2), ("cvHI", lambda r: r["cv"] >= c2)):
        sub = [r for r in rows if tf(r)]
        if len(sub) < 60: continue
        qm = statistics.median(x["qconc"] for x in sub)
        for ql, qf in (("concHI", lambda r: r["qconc"] >= qm), ("concLO", lambda r: r["qconc"] < qm)):
            g = [r for r in sub if qf(r)]
            if len(g) < 60: continue
            roi = sum((r["over_od"] - 1) if r["over_won"] else -1.0 for r in g) / len(g)
            om = statistics.mean(r["over_od"] for r in g); se = om / math.sqrt(len(g))
            print("   %-5s %-5s %-7s n=%-4d over%% %.1f  OVER ROI %+6.2f%% CI[%+0.1f,%+0.1f]" % (
                gname, tl, ql, len(g), 100 * sum(1 for r in g if r["over_won"]) / len(g),
                100 * roi, 100 * (roi - 1.96 * se), 100 * (roi + 1.96 * se)))
print("\nbase rates: board over%% = %.1f  (n=%d)" % (100 * sum(1 for r in R if r["over_won"]) / len(R), len(R)))
print("done")
