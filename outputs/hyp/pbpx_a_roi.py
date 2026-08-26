import csv, os, sys, math, collections, random, statistics
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
random.seed(20260826)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pbpx_lib import *

rows = load_master()
S = series(rows)
MINPRS = (5, 10)
for k, v in S.items():
    for i, r in enumerate(v):
        pri = [p for p in v[:i] if p["tpa"] >= 5]
        r["n_prior"] = len(pri)
        r["z3"] = None
        if len(pri) >= 5 and r["tp_pct"] is not None:
            bp = sum(p["tpm"] for p in pri) / sum(p["tpa"] for p in pri)
            sd = statistics.pstdev([p["tp_pct"] for p in pri])
            r["z3"] = (r["tp_pct"] - bp) / sd if sd > 0 else None
        r["nxt"] = v[i + 1] if i + 1 < len(v) else None

# ---------------- GRID DECLARED BEFORE LOOKING ----------------
ZT = (1.5, 2.0, 2.5)
MP = (5, 10)
TA = (0, 20)
GRID = [(z, m, a) for z in ZT for m in MP for a in TA]
print("GRID: %d cells = z_thresh%s x min_prior%s x min_3PA%s ; bet = UNDER the next game total" % (len(GRID), ZT, MP, TA))


def bets_for(cell, zmap):
    z, mp, ta = cell
    out = []
    for r in rows:
        zz = zmap.get(id(r))
        if zz is None or r["nxt"] is None:
            continue
        if r["n_prior"] < mp or r["tpa"] < ta or zz < z:
            continue
        nx = r["nxt"]
        if nx["ou_u"] is None or nx["total"] is None:
            continue
        out.append(nx)
    # one bet per game (dedupe if both teams qualify)
    seen = {}
    for nx in out:
        seen.setdefault(nx["game_id"], nx)
    res = []
    for gid, nx in seen.items():
        gt = nx["game_total"]
        if abs(gt - nx["total"]) < 1e-9:
            p = 0.0
        elif gt < nx["total"]:
            p = nx["ou_u"] - 1.0
        else:
            p = -1.0
        res.append((gid, p))
    return res


def evaluate(zmap):
    best = None
    tab = []
    for cell in GRID:
        bs = bets_for(cell, zmap)
        if len(bs) < 25:
            tab.append((cell, len(bs), None))
            continue
        roi = sum(p for _, p in bs) / len(bs)
        tab.append((cell, len(bs), roi))
        if best is None or roi > best[0]:
            best = (roi, cell, len(bs))
    return best, tab


zmap = {id(r): r["z3"] for r in rows}

# ---------------- NOISE CEILING (permute z3 within team-season, circular shift) ----------------
NPERM = 400
rnd = random.Random(20260826)
null_best = []
for _ in range(NPERM):
    zm = {}
    for k, v in S.items():
        zz = [r["z3"] for r in v]
        s = rnd.randrange(len(v))
        zz = zz[s:] + zz[:s]
        for r, val in zip(v, zz):
            zm[id(r)] = val
    b, _ = evaluate(zm)
    if b:
        null_best.append(b[0])
null_best.sort()
p95 = null_best[int(0.95 * len(null_best))]
p50 = null_best[len(null_best) // 2]
print("NOISE CEILING under the null (circular shift of the hot-label within team-season, %d perms):" % NPERM)
print("  best-of-%d-cells ROI: median %+.2f%%   p95 = %+.2f%%   <-- a real finding must clear this" % (len(GRID), 100 * p50, 100 * p95))

best, tab = evaluate(zmap)
print("\n%-22s %6s %9s %8s" % ("cell (z,minprior,min3PA)", "n_games", "ROI", "vs p95"))
for cell, n, roi in tab:
    if roi is None:
        print("%-22s %6d %9s" % (str(cell), n, "-- thin --"))
    else:
        print("%-22s %6d %+8.2f%% %8s" % (str(cell), n, 100 * roi, "CLEARS" if roi > p95 else ""))
print("\nBEST CELL: %s  n=%d  ROI %+.2f%%   noise p95 %+.2f%%  -> %s" %
      (best[1], best[2], 100 * best[0], 100 * p95, "CLEARS" if best[0] > p95 else "UNDER CEILING (not a finding)"))

# headline cell with CI
for cell in ((2.0, 5, 0), (1.5, 5, 0)):
    bs = bets_for(cell, zmap)
    units = [[p] for _, p in bs]
    m, lo, hi = block_boot(units, 4000, 7)
    w = sum(1 for _, p in bs if p > 0)
    ps = sum(1 for _, p in bs if p == 0)
    print("  cell %s: n=%d games (independent units=%d) under-hit %d-%d-%d = %.1f%%  ROI %+.2f%% CI[%+.2f%%, %+.2f%%]" %
          (cell, len(bs), len(bs), w, len(bs) - w - ps, ps, 100 * w / max(len(bs) - ps, 1), 100 * m, 100 * lo, 100 * hi))

# also report the OVER side of the same gate, to show it is a coin flip not a one-sided artifact
for cell in ((2.0, 5, 0),):
    z, mp, ta = cell
    seen = {}
    for r in rows:
        if r["z3"] is None or r["nxt"] is None or r["n_prior"] < mp or r["tpa"] < ta or r["z3"] < z:
            continue
        nx = r["nxt"]
        if nx["ou_o"] is None:
            continue
        seen.setdefault(nx["game_id"], nx)
    ps = []
    for gid, nx in seen.items():
        gt = nx["game_total"]
        ps.append(0.0 if gt == nx["total"] else (nx["ou_o"] - 1.0 if gt > nx["total"] else -1.0))
    print("  same gate, OVER side: n=%d ROI %+.2f%%   (over+under both negative => plain vig, no line error)" % (len(ps), 100 * sum(ps) / len(ps)))
