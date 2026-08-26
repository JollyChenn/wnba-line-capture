# =====================================================================================
# DIMENSION: WITHIN-GAME TIMING  -  does WHEN a player produces predict her full-game prop?
# Fast, exact re-implementation of the declared grid + player-block noise ceiling.
# Features are player-level constants taken from her FIRST board-row profile (strictly
# walk-forward: built only from games with tip < that game), so the null that matters is a
# PLAYER-BLOCK relabel (Law 2).  Prices are real two-sided board quotes at the SAME line.
# =====================================================================================
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
xs = [FEAT0[p]["cv"] for p in FEAT0]; ys = [FEAT0[p]["qconc"] for p in FEAT0]
mx, my = statistics.mean(xs), statistics.mean(ys)
bb = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
aa = my - bb * mx
for p in FEAT0: FEAT0[p]["qconc_r"] = FEAT0[p]["qconc"] - (aa + bb * FEAT0[p]["cv"])
for r in R: r.update(FEAT0[r["pl"]])
FEATS = ("h1share", "q4share", "qconc", "qconc_r", "q4app")
print("rows %d  players %d  games %d  over%% %.1f" %
      (len(R), len(FEAT0), len(set(r['gt'] for r in R)), 100 * sum(1 for r in R if r["over_won"]) / len(R)))

# ---- per-player aggregates per market group (exactly reproduces a row-level cell) ----
GRPS = (("ALL", ALL_MK), ("SCOR", SCOR), ("NONS", NONS))
AGG = {}
for gname, grp in GRPS:
    d = {}
    for r in R:
        if r["mk"] not in grp: continue
        a = d.setdefault(r["pl"], [0, 0.0, 0.0, 0])          # n, sum_over_pnl, sum_under_pnl, wins
        a[0] += 1
        a[1] += (r["over_od"] - 1) if r["over_won"] else -1.0
        a[2] += (r["under_od"] - 1) if not r["over_won"] else -1.0
        a[3] += 1 if r["over_won"] else 0
    AGG[gname] = d
PLS = sorted(FEAT0)
SPLITS = ("HI", "LO", "T3HI", "T3LO")
MINN = 120
CELLS = [(ft, gn, sp, w) for ft in FEATS for gn, _ in GRPS for sp in SPLITS for w in ("over", "under")]
print("GRID DECLARED: %d cells = %d features x %d market groups x %d splits x 2 sides, MINN=%d"
      % (len(CELLS), len(FEATS), len(GRPS), len(SPLITS), MINN))

def cell_roi(featvals, ft, gn, sp, w):
    d = AGG[gn]
    ps = [p for p in PLS if p in d]
    ps.sort(key=lambda p: featvals[p][ft])
    tot = sum(d[p][0] for p in ps)
    def val_at(idx):
        c = 0
        for p in ps:
            c += d[p][0]
            if c > idx: return featvals[p][ft]
        return featvals[ps[-1]][ft]
    if sp in ("HI", "LO"):
        c = val_at(tot // 2)
        sel = [p for p in ps if (featvals[p][ft] >= c if sp == "HI" else featvals[p][ft] < c)]
    else:
        lo = val_at(tot // 3); hi = val_at(2 * tot // 3)
        sel = [p for p in ps if (featvals[p][ft] >= hi if sp == "T3HI" else featvals[p][ft] < lo)]
    n = sum(d[p][0] for p in sel)
    if n < MINN: return None
    s = sum(d[p][1 if w == "over" else 2] for p in sel)
    return s / n, n, sum(d[p][3] for p in sel)

def all_cells(featvals):
    out = []
    for ft, gn, sp, w in CELLS:
        c = cell_roi(featvals, ft, gn, sp, w)
        if c: out.append((c[0], c[1], c[2], "%s %s [%s] %s" % (ft, sp, w, gn)))
    return out

# ---------------- NOISE CEILING FIRST ----------------
NPERM = 4000
best = []
donors = list(PLS)
for _ in range(NPERM):
    random.shuffle(donors)
    fv = {p: FEAT0[q] for p, q in zip(PLS, donors)}
    c = all_cells(fv)
    if c: best.append(max(x[0] for x in c))
best.sort()
CEIL95 = best[int(0.95 * len(best))]; CEIL99 = best[int(0.99 * len(best))]
print("NOISE CEILING (player-block relabel, %d perms, 107 player blocks): p95 best-cell ROI = %+0.2f%%  p99 = %+0.2f%%"
      % (NPERM, 100 * CEIL95, 100 * CEIL99))
print("   null best-cell median %+0.2f%%   null best-cell 5th pct %+0.2f%%"
      % (100 * statistics.median(best), 100 * best[int(0.05 * len(best))]))

# ---------------- REAL ----------------
real = all_cells(FEAT0); real.sort(reverse=True)
print("\n" + "=" * 96)
print("REAL CELLS, ranked.  CEILING p95 = %+0.2f%%   (breakeven is ~53.5%%, board margin ~7%%)" % (100 * CEIL95))
print("=" * 96)
for roi, n, wins, lab in real:
    pv = (sum(1 for x in best if x >= roi) + 1) / (len(best) + 1)
    # CI from mean odds of the graded side
    flag = "  <<< BEATS CEILING" if roi > CEIL95 else ""
    print("  %-30s n=%-5d win%% %.1f  ROI %+6.2f%%  p(global)=%.3f%s" % (lab, n, 100 * wins / n if lab.find("[over]") > 0 else 100 * (n - wins) / n, 100 * roi, pv, flag))

# ---------------- CI on the top cells ----------------
print("\nCI on the 5 best and 5 worst cells (normal approx on realised pnl):")
def cellrows(ft, gn, sp, w):
    grp = dict(GRPS)[gn]
    d = AGG[gn]; ps = [p for p in PLS if p in d]; ps.sort(key=lambda p: FEAT0[p][ft])
    tot = sum(d[p][0] for p in ps)
    def val_at(idx):
        c = 0
        for p in ps:
            c += d[p][0]
            if c > idx: return FEAT0[p][ft]
        return FEAT0[ps[-1]][ft]
    if sp in ("HI", "LO"):
        c = val_at(tot // 2); sel = set(p for p in ps if (FEAT0[p][ft] >= c if sp == "HI" else FEAT0[p][ft] < c))
    else:
        lo = val_at(tot // 3); hi = val_at(2 * tot // 3)
        sel = set(p for p in ps if (FEAT0[p][ft] >= hi if sp == "T3HI" else FEAT0[p][ft] < lo))
    return [r for r in R if r["mk"] in grp and r["pl"] in sel]
for roi, n, wins, lab in real[:5] + real[-5:]:
    ft, sp, wtag, gn = lab.split()
    w = wtag.strip("[]")
    rows = cellrows(ft, gn, sp, w)
    pn = [((r["over_od"] - 1) if r["over_won"] else -1.0) if w == "over"
          else ((r["under_od"] - 1) if not r["over_won"] else -1.0) for r in rows]
    sd = statistics.pstdev(pn); se = sd / math.sqrt(len(pn))
    print("   %-30s n=%-5d ROI %+6.2f%%  CI [%+0.1f%%, %+0.1f%%]" % (lab, len(pn), 100 * roi, 100 * (roi - 1.96 * se), 100 * (roi + 1.96 * se)))

# ---------------- monotone gradient view (quintiles of each feature, OVER side) ----------------
print("\nQuintile gradient, OVER side, scoring markets (pts/pra/pr/pa):")
rows_s = [r for r in R if r["mk"] in SCOR]
for ft in FEATS:
    vs = sorted(r[ft] for r in rows_s)
    qs = [vs[int(k * len(vs) / 5)] for k in range(1, 5)]
    line = []
    for k in range(5):
        lo = -1e9 if k == 0 else qs[k - 1]; hi = 1e9 if k == 4 else qs[k]
        g = [r for r in rows_s if lo <= r[ft] < hi]
        if not g: line.append("   n/a "); continue
        roi = sum((r["over_od"] - 1) if r["over_won"] else -1.0 for r in g) / len(g)
        line.append("%+5.1f%%(%d)" % (100 * roi, len(g)))
    print("   %-9s  " % ft + "  ".join(line))

json.dump({"ceil95": CEIL95, "ceil99": CEIL99, "real": real}, open(os.path.join(D, "tim_grid.json"), "w"))
print("\nwrote tim_grid.json")
