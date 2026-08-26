# xm_cross.py - CROSS-MODEL CORRELATION AND COMBINATION
# Grid declared up front, noise ceiling computed under a player-block null BEFORE the real table.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])

# =============================================================== 1. FIRING TABLE
L = load("bets_log.csv")
FIRE = {}
for r in L:
    pl = (r.get("player") or "").lower(); mk = r.get("market"); sd = r.get("side")
    src = r.get("src") or ""; ln = f(r.get("line")); od = f(r.get("odds")); cap = ts(r.get("captured_utc"))
    if not (pl and mk and sd and cap and ln is not None and od): continue
    tm = teamof.get(pl)
    if not tm: continue
    gt = game_for(tm, cap)
    if not gt: continue
    k = (src, pl, mk, gt)
    cur = FIRE.get(k)
    if cur is None or cap < cur["cap"]:
        FIRE[k] = dict(src=src, pl=pl, mk=mk, gt=gt, side=sd, line=ln, odds=od, cap=cap,
                       tier=r.get("tier"), ev=f(r.get("ev")), date=r.get("date"), tm=tm)

GID = {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    GID[(hm, t2)] = gid; GID[(aw, t2)] = gid

ROWS = []
for k, v in FIRE.items():
    row = pgrow.get((v["pl"], v["gt"]))
    if not row: continue
    act = row.get(v["mk"])
    if act is None or act == v["line"]: continue          # push dropped
    won = (act > v["line"]) if v["side"] == "Over" else (act < v["line"])
    pv = prevline.get((v["pl"], v["mk"], v["gt"]))
    ROWS.append(dict(v, act=act, won=won, pnl=(v["odds"]-1) if won else -1.0,
                     gid=GID.get((v["tm"], v["gt"])),
                     raised=(None if pv is None else (v["line"]-pv) >= 0.5)))
print("settled fires: %d   players: %d   player-games: %d   slates: %d" % (
      len(ROWS), len(set(r["pl"] for r in ROWS)),
      len(set((r["pl"], r["gt"]) for r in ROWS)), len(set(r["date"] for r in ROWS))))

# =============================================================== 2. PG-LEVEL BUNDLE
pg_srcs = collections.defaultdict(set); pg_sides = collections.defaultdict(set)
pgm_srcs = collections.defaultdict(set)
for r in ROWS:
    pg_srcs[(r["pl"], r["gt"])].add(r["src"])
    pg_sides[(r["pl"], r["gt"])].add(r["side"])
    pgm_srcs[(r["pl"], r["mk"], r["gt"])].add(r["src"])

OVERF = {"cascade", "overshoot", "flip_paper", "flip", "hotover", "usgshock"}
UNDERF = {"newunder", "model", "starout", "fragile"}

BUND = {}
for r in ROWS:
    s = pg_srcs[(r["pl"], r["gt"])]; sm = pgm_srcs[(r["pl"], r["mk"], r["gt"])]
    BUND[(r["pl"], r["gt"], r["mk"])] = dict(
        srcs=frozenset(s), srcs_mk=frozenset(sm),
        n_over=len(s & OVERF), n_under=len(s & UNDERF), n_all=len(s),
        contra=(len(pg_sides[(r["pl"], r["gt"])]) > 1))

# =============================================================== 3. GRID, DECLARED UP FRONT
SIGS_S = ("flip", "hotover", "overshoot"); BET_MK = ("pra", "pr", "pts")
def is_S(r): return r["src"] in SIGS_S and r["mk"] in BET_MK and r["raised"] is not None and not r["raised"]

CELLS = []
def C(name, fn): CELLS.append((name, fn))
for n in (1, 2, 3):
    C("OVERfam, exactly %d over-families agree" % n, lambda r, b, n=n: r["src"] in OVERF and b["n_over"] == n)
for n in (2, 3):
    C("OVERfam, >=%d over-families agree" % n, lambda r, b, n=n: r["src"] in OVERF and b["n_over"] >= n)
C("OVERfam, 2+ families SAME market slot", lambda r, b: r["src"] in OVERF and len(b["srcs_mk"] & OVERF) >= 2)
C("OVERfam, only family on that slot", lambda r, b: r["src"] in OVERF and len(b["srcs_mk"] & OVERF) == 1)
for n in (1, 2):
    C("UNDERfam, exactly %d under-families agree" % n, lambda r, b, n=n: r["src"] in UNDERF and b["n_under"] == n)
C("OVERfam, contradicted by an under-fam", lambda r, b: r["src"] in OVERF and b["contra"])
C("OVERfam, NOT contradicted", lambda r, b: r["src"] in OVERF and not b["contra"])
C("UNDERfam, contradicted by an over-fam", lambda r, b: r["src"] in UNDERF and b["contra"])
C("UNDERfam, NOT contradicted", lambda r, b: r["src"] in UNDERF and not b["contra"])
C("Model S (live)", lambda r, b: is_S(r))
C("Model S + another over-fam agrees", lambda r, b: is_S(r) and b["n_over"] >= 2)
C("Model S alone (no other over-fam)", lambda r, b: is_S(r) and b["n_over"] == 1)
C("Model S + contradicted by under-fam", lambda r, b: is_S(r) and b["contra"])
C("Model S + NOT contradicted", lambda r, b: is_S(r) and not b["contra"])
PAIRS = [("overshoot", "flip_paper"), ("cascade", "newunder"), ("cascade", "flip_paper"),
         ("newunder", "overshoot"), ("newunder", "hotover"), ("flip", "model"),
         ("flip", "hotover"), ("cascade", "starout"), ("newunder", "flip_paper"),
         ("overshoot", "hotover"), ("flip_paper", "cascade"), ("overshoot", "newunder")]
for a, b_ in PAIRS:
    C("pair: %s confirmed by %s" % (a, b_), lambda r, bb, a=a, b_=b_: r["src"] == a and b_ in bb["srcs"])
    C("pair: %s WITHOUT %s" % (a, b_), lambda r, bb, a=a, b_=b_: r["src"] == a and b_ not in bb["srcs"])
print("\nGRID: %d cells declared. min n = 25." % len(CELLS))
CELLD = dict(CELLS)

MINN = 25
def roi(rows):
    return 100 * statistics.mean([r["pnl"] for r in rows]) if rows else None
def ci95(rows):
    p = [r["pnl"] for r in rows]; n = len(p)
    if n < 2: return (float("nan"), float("nan"))
    m = statistics.mean(p); h = 1.96 * statistics.pstdev(p) / math.sqrt(n)
    return (100 * (m - h), 100 * (m + h))

def eval_grid(bmap):
    out = []
    for name, fn in CELLS:
        sel = [r for r in ROWS if fn(r, bmap[(r["pl"], r["gt"], r["mk"])])]
        if len(sel) >= MINN: out.append((name, len(sel), roi(sel)))
    return out

# =============================================================== 4. NOISE CEILING
byplayer = collections.defaultdict(list)
for r in ROWS: byplayer[r["pl"]].append(r)
players = sorted(byplayer)
KEYS = {p: sorted({(r["gt"], r["mk"]) for r in byplayer[p]}) for p in players}
SEQ = {p: [BUND[(p, gt, mk)] for gt, mk in KEYS[p]] for p in players}

def perm_bundles(rng):
    donors = players[:]; rng.shuffle(donors)
    out = {}
    for i, p in enumerate(players):
        d = SEQ[donors[i]]
        for j, (gt, mk) in enumerate(KEYS[p]):
            out[(p, gt, mk)] = d[j % len(d)]
    return out

NPERM = 500
rng = random.Random(20260826)
best = []
for it in range(NPERM):
    g = eval_grid(perm_bundles(rng))
    if g: best.append(max(x[2] for x in g))
best.sort()
CEIL = best[int(0.95 * len(best))]
print("\nNOISE CEILING (player-block relabel, %d perms, best-of-grid ROI):" % NPERM)
print("    p50 %+.1f%%   p90 %+.1f%%   p95 %+.1f%%   p99 %+.1f%%   max %+.1f%%" % (
      best[len(best) // 2], best[int(0.90 * len(best))], CEIL,
      best[int(0.99 * len(best))], best[-1]))
print("    >>> ANY CELL AT OR BELOW %+.1f%% IS NOT A FINDING <<<" % CEIL)

# =============================================================== 5. REAL TABLE
real = eval_grid(BUND)
print("\n%-46s%5s%9s%19s  %s" % ("cell", "n", "ROI%", "CI95", "vs ceiling"))
for name, n, rr in sorted(real, key=lambda x: -x[2]):
    sel = [r for r in ROWS if CELLD[name](r, BUND[(r["pl"], r["gt"], r["mk"])])]
    lo, hi = ci95(sel)
    print("%-46s%5d%8.1f%%   [%6.1f,%6.1f]  %s" % (name, n, rr, lo, hi, "BEATS" if rr > CEIL else ""))

print("\nper-cell player-block p-values (top 6 cells):")
for name, n, rr in sorted(real, key=lambda x: -x[2])[:6]:
    fn = CELLD[name]; rng2 = random.Random(99); cnt = 0; tot = 0
    for _ in range(1200):
        bm = perm_bundles(rng2)
        sel = [r for r in ROWS if fn(r, bm[(r["pl"], r["gt"], r["mk"])])]
        if len(sel) < MINN: continue
        tot += 1
        if roi(sel) >= rr: cnt += 1
    print("  %-46s n=%4d ROI %+6.1f%%  p=%.4f" % (name, n, rr, (cnt + 1) / (tot + 1)))
