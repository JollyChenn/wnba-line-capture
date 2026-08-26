# WITHIN-GAME TIMING dimension: does WHEN a player scores predict her full-game prop?
import csv, os, sys, math, random, statistics, datetime, collections, re, json
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])

R = json.load(open(os.path.join(D, "tim_rows.json")))
print("rows %d  players %d  games %d" % (len(R), len(set(r['pl'] for r in R)), len(set(r['gt'] for r in R))))

# ---- final margin per game (blowout cross) ----
marg = {}
for g in load("data/games_2026.csv"):
    hs, a_ = f(g.get("home_score")), f(g.get("away_score"))
    if hs is None or a_ is None: continue
    marg[(g.get("date"), g.get("home"))] = hs - a_
    marg[(g.get("date"), g.get("away"))] = a_ - hs
for r in R:
    r["margin"] = marg.get((r["date"], r["tm"]))
    r["absmarg"] = abs(r["margin"]) if r["margin"] is not None else None

SCOR = ("pts", "pra", "pr", "pa")
NONS = ("reb", "ast", "ra")

# ---- player-level constant feature = profile at her FIRST board row (strictly walk-forward) ----
byp = collections.defaultdict(list)
for r in R: byp[r["pl"]].append(r)
for v in byp.values(): v.sort(key=lambda x: x["gt"])
FEAT0 = {}
for pl, v in byp.items():
    z = v[0]
    FEAT0[pl] = dict(h1share=z["h1share"], q4share=z["q4share"], qconc=z["qconc"],
                     q4app=z["q4app"], cv=z["cv"])

def sprho(u, v):
    n = len(u)
    ru = {}; rv = {}
    for arr, d in ((u, ru), (v, rv)):
        order = sorted(range(n), key=lambda i: arr[i]); i = 0
        while i < n:
            j = i
            while j + 1 < n and arr[order[j + 1]] == arr[order[i]]: j += 1
            rk = (i + j) / 2 + 1
            for k in range(i, j + 1): d[order[k]] = rk
            i = j + 1
    mu = (n + 1) / 2
    su = math.sqrt(sum((ru[i] - mu) ** 2 for i in range(n)))
    sv = math.sqrt(sum((rv[i] - mu) ** 2 for i in range(n)))
    if su == 0 or sv == 0: return 0.0
    return sum((ru[i] - mu) * (rv[i] - mu) for i in range(n)) / (su * sv)

# qconc residualised on cv  (THE control: does concentration add anything beyond total variance?)
xs = [FEAT0[p]["cv"] for p in FEAT0]; ys = [FEAT0[p]["qconc"] for p in FEAT0]
mx, my = statistics.mean(xs), statistics.mean(ys)
bb = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
aa = my - bb * mx
for p in FEAT0: FEAT0[p]["qconc_r"] = FEAT0[p]["qconc"] - (aa + bb * FEAT0[p]["cv"])
print("qconc ~ cv   : slope %.3f  spearman rho %.3f  (n players %d)" % (bb, sprho(xs, ys), len(xs)))
print("h1share ~ cv : rho %.3f" % sprho([FEAT0[p]['cv'] for p in FEAT0], [FEAT0[p]['h1share'] for p in FEAT0]))
print("q4share~h1sh : rho %.3f" % sprho([FEAT0[p]['h1share'] for p in FEAT0], [FEAT0[p]['q4share'] for p in FEAT0]))
print("q4app ~ cv   : rho %.3f" % sprho([FEAT0[p]['cv'] for p in FEAT0], [FEAT0[p]['q4app'] for p in FEAT0]))
for r in R:
    r.update({k: v for k, v in FEAT0[r["pl"]].items()})

FEATS = ("h1share", "q4share", "qconc", "qconc_r", "q4app")

# =====================================================================
# STEP 1  MECHANISM (Law 6) - test the DIRECTION on raw production first
# =====================================================================
print("\n" + "=" * 92)
print("MECHANISM CHECK on raw production (residual = actual - line), BEFORE any ROI")
print("=" * 92)

def clustered_p(rows, key, val, nperm=800):
    u = [r[key] for r in rows]; v = [r[val] for r in rows]
    obs = sprho(u, v)
    pls = sorted(set(r["pl"] for r in rows))
    fv = {p: FEAT0[p][key] for p in pls}
    idx = [r["pl"] for r in rows]
    donors = list(pls); cnt = 0
    for _ in range(nperm):
        random.shuffle(donors)
        mp = dict(zip(pls, donors))
        uu = [fv[mp[p]] for p in idx]
        if abs(sprho(uu, v)) >= abs(obs): cnt += 1
    return obs, (cnt + 1) / (nperm + 1)

for grp, name in ((SCOR, "scoring mkts"), (NONS, "non-scoring")):
    rows = [r for r in R if r["mk"] in grp]
    for k in FEATS:
        rho, p = clustered_p(rows, k, "resid", 600)
        print("  %-12s %-9s vs residual  rho %+0.4f  p(player-block) %.3f  n %d" % (name, k, rho, p, len(rows)))

print("\n  blowout cross (absmarg>=12 vs <12), scoring markets, mean residual:")
rows = [r for r in R if r["mk"] in SCOR and r["absmarg"] is not None]
med_h1 = statistics.median(FEAT0[p]["h1share"] for p in FEAT0)
med_q4 = statistics.median(FEAT0[p]["q4share"] for p in FEAT0)
for lab, fn in (("h1share HIGH", lambda r: r["h1share"] >= med_h1), ("h1share LOW", lambda r: r["h1share"] < med_h1),
                ("q4share HIGH", lambda r: r["q4share"] >= med_q4), ("q4share LOW", lambda r: r["q4share"] < med_q4)):
    for bl, bf in (("blowout", lambda r: r["absmarg"] >= 12), ("close", lambda r: r["absmarg"] < 12)):
        g = [r for r in rows if fn(r) and bf(r)]
        if len(g) < 40: continue
        print("    %-14s %-8s n=%-5d mean resid %+0.3f  over%% %.1f" % (
            lab, bl, len(g), statistics.mean(x['resid'] for x in g),
            100 * sum(1 for x in g if x['over_won']) / len(g)))

# =====================================================================
# STEP 2  DECLARE THE GRID, THEN THE NOISE CEILING - BEFORE real results
# =====================================================================
GRPS = (("ALL", ALL_MK), ("SCOR", SCOR), ("NONS", NONS))
SPLITS = ("HI", "LO", "T3HI", "T3LO")
MINN = 120
CELLS = []
for feat in FEATS:
    for gname, grp in GRPS:
        for s_ in SPLITS:
            for w in ("over", "under"):
                CELLS.append((feat, gname, grp, s_, w))
print("\nGRID DECLARED: %d cells (%d features x %d market groups x %d splits x 2 sides), MINN=%d"
      % (len(CELLS), len(FEATS), len(GRPS), len(SPLITS), MINN))

ROWS_BY_GRP = {gname: [r for r in R if r["mk"] in grp] for gname, grp in GRPS}

def roi_cells(featmap):
    out = []
    for feat, gname, grp, s_, w in CELLS:
        rows = ROWS_BY_GRP[gname]
        vals = [featmap[r["pl"]][feat] for r in rows]
        v = sorted(vals)
        if s_ in ("HI", "LO"):
            c = v[len(v) // 2]
            sel = [r for r, x in zip(rows, vals) if (x >= c if s_ == "HI" else x < c)]
        else:
            lo = v[len(v) // 3]; hi = v[2 * len(v) // 3]
            sel = [r for r, x in zip(rows, vals) if (x >= hi if s_ == "T3HI" else x < lo)]
        if len(sel) < MINN: continue
        if w == "over":
            roi = sum((r["over_od"] - 1) if r["over_won"] else -1.0 for r in sel) / len(sel)
        else:
            roi = sum((r["under_od"] - 1) if not r["over_won"] else -1.0 for r in sel) / len(sel)
        out.append((roi, len(sel), "%s %s [%s] %s" % (feat, s_, w, gname)))
    return out

PLS = sorted(FEAT0)
NPERM = 1500
best = []
for _ in range(NPERM):
    d = list(PLS); random.shuffle(d)
    fm = {p: FEAT0[q] for p, q in zip(PLS, d)}
    c = roi_cells(fm)
    if c: best.append(max(x[0] for x in c))
best.sort()
CEIL95 = best[int(0.95 * len(best))]; CEIL99 = best[int(0.99 * len(best))]
print("NOISE CEILING (player-block relabel, %d perms): p95 best-cell ROI = %+0.2f%%   p99 = %+0.2f%%"
      % (NPERM, 100 * CEIL95, 100 * CEIL99))
print("   (null best-cell median %+0.2f%%,  null best-cell min %+0.2f%%)"
      % (100 * statistics.median(best), 100 * best[0]))

# =====================================================================
# STEP 3  REAL RESULTS
# =====================================================================
real = roi_cells(FEAT0); real.sort(reverse=True)
print("\n" + "=" * 92)
print("REAL CELLS (n>=%d).  CEILING p95 = %+0.2f%%" % (MINN, 100 * CEIL95))
print("=" * 92)

def show(lst):
    for roi, n, lab in lst:
        pv = (sum(1 for x in best if x >= roi) + 1) / (len(best) + 1)
        flag = "BEATS CEILING" if roi > CEIL95 else ""
        print("  %-34s n=%-5d ROI %+6.2f%%   p(global)=%.3f %s" % (lab, n, 100 * roi, pv, flag))

show(real[:14]); print("  ...")
show(real[-8:])
json.dump({"ceil95": CEIL95, "ceil99": CEIL99, "real": real}, open(os.path.join(D, "tim_grid.json"), "w"))
print("\nwrote tim_grid.json")
