# xm_cross4.py - GRID B: the confidence layer (tier / ev), with its own declared grid and
# noise ceiling; plus a corrected rank-correlation and a permutation test on the slate-level
# family-vs-family correlations.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])

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
    k = (src, pl, mk, gt); cur = FIRE.get(k)
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
    if act is None or act == v["line"]: continue
    won = (act > v["line"]) if v["side"] == "Over" else (act < v["line"])
    pv = prevline.get((v["pl"], v["mk"], v["gt"]))
    ROWS.append(dict(v, act=act, won=won, pnl=(v["odds"] - 1) if won else -1.0,
                     gid=GID.get((v["tm"], v["gt"])),
                     ph=((1 + v["ev"]) / v["odds"]) if v["ev"] is not None else None,
                     raised=(None if pv is None else (v["line"] - pv) >= 0.5)))
OVERF = {"cascade", "overshoot", "flip_paper", "flip", "hotover", "usgshock"}
SIGS_S = ("flip", "hotover", "overshoot"); BET_MK = ("pra", "pr", "pts")
def is_S(r): return r["src"] in SIGS_S and r["mk"] in BET_MK and r["raised"] is not None and not r["raised"]
def roi(rows): return 100 * statistics.mean([r["pnl"] for r in rows]) if rows else float("nan")
def ci95(rows):
    p = [r["pnl"] for r in rows]; n = len(p)
    if n < 2: return (float("nan"), float("nan"))
    m = statistics.mean(p); h = 1.96 * statistics.pstdev(p) / math.sqrt(n)
    return (100 * (m - h), 100 * (m + h))
def pear(xs, ys):
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    dx = math.sqrt(sum((a - mx) ** 2 for a in xs)); dy = math.sqrt(sum((b - my) ** 2 for b in ys))
    return num / (dx * dy) if dx and dy else 0.0
def tied_rank(v):
    o = sorted(range(len(v)), key=lambda i: v[i]); rr = [0.0] * len(v); i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]: j += 1
        avg = (i + j) / 2.0 + 1
        for kk in range(i, j + 1): rr[o[kk]] = avg
        i = j + 1
    return rr
def spearman(xs, ys): return pear(tied_rank(xs), tied_rank(ys))

# ================================================== corrected rank correlation, whole pool
cal = [r for r in ROWS if r["ph"] is not None and 0.01 < r["ph"] < 0.999]
xs = [r["ph"] for r in cal]; ys = [1.0 if r["won"] else 0.0 for r in cal]
rho = spearman(xs, ys)
byp = collections.defaultdict(list)
for r in cal: byp[r["pl"]].append(r)
pls = sorted(byp)
FLAT = [r for p in pls for r in byp[p]]                 # canonical order used by the null
xs2 = [r["ph"] for r in FLAT]; ys2 = [1.0 if r["won"] else 0.0 for r in FLAT]
assert abs(spearman(xs2, ys2) - rho) < 1e-9
rng = random.Random(11); cnt = 0; NP = 3000
for _ in range(NP):
    dn = pls[:]; rng.shuffle(dn); xx = []
    for i, p in enumerate(pls):
        d = [r["ph"] for r in byp[dn[i]]]
        for j in range(len(byp[p])): xx.append(d[j % len(d)])
    if abs(spearman(xx, ys2)) >= abs(rho): cnt += 1
print("CONFIDENCE LAYER, pooled across ALL families, n=%d" % len(cal))
print("  spearman(engine predicted hit, bet won) = %+.4f   player-block p = %.4f  (tied ranks, fixed)"
      % (rho, (cnt + 1) / (NP + 1)))
print("  mean predicted hit %.1f%%   realised %.1f%%   -> level bias %+.1f pp"
      % (100 * statistics.mean(xs), 100 * statistics.mean(ys), 100 * (statistics.mean(ys) - statistics.mean(xs))))
# same within over-families only (the side confound removed)
ov = [r for r in cal if r["src"] in OVERF]
print("  within OVER-families only: spearman = %+.4f  (n=%d)"
      % (spearman([r["ph"] for r in ov], [1.0 if r["won"] else 0.0 for r in ov]), len(ov)))
un = [r for r in cal if r["src"] not in OVERF]
print("  within UNDER-families only: spearman = %+.4f  (n=%d)"
      % (spearman([r["ph"] for r in un], [1.0 if r["won"] else 0.0 for r in un]), len(un)))

# ================================================== GRID B: tier / ev cells
CELLS = []
def C(n, fn): CELLS.append((n, fn))
POOLS = [("OVERfam", lambda r: r["src"] in OVERF), ("ModelS", is_S),
         ("ALL", lambda r: True), ("UNDERfam", lambda r: r["src"] not in OVERF)]
for pn, pf in POOLS:
    for t in ("STRONG", "SOLID", "THIN"):
        C("%s tier=%s" % (pn, t), lambda r, pf=pf, t=t: pf(r) and r["tier"] == t)
    C("%s tier=THIN or SOLID" % pn, lambda r, pf=pf: pf(r) and r["tier"] in ("THIN", "SOLID"))
qs = sorted(r["ph"] for r in cal)
Q = [qs[int(x * len(qs))] for x in (0.2, 0.4, 0.6, 0.8)]
for pn, pf in POOLS:
    C("%s ph quintile 1 (lowest)" % pn, lambda r, pf=pf: pf(r) and r["ph"] is not None and r["ph"] < Q[0])
    C("%s ph quintile 5 (highest)" % pn, lambda r, pf=pf: pf(r) and r["ph"] is not None and r["ph"] >= Q[3])
    C("%s ph below median" % pn, lambda r, pf=pf: pf(r) and r["ph"] is not None and r["ph"] < Q[1])
    C("%s ph above median" % pn, lambda r, pf=pf: pf(r) and r["ph"] is not None and r["ph"] >= Q[2])
print("\nGRID B: %d cells declared (tier x pool, ph quantile x pool). min n = 25." % len(CELLS))
CELLD = dict(CELLS); MINN = 25

# null: the label is the fire's own (tier, ph). Confounds = family and player.
# So permute (tier, ph) WITHIN family, handing one player's label-vector to another player.
famplayers = {}
for s in set(r["src"] for r in ROWS):
    d = collections.defaultdict(list)
    for r in ROWS:
        if r["src"] == s: d[r["pl"]].append(r)
    famplayers[s] = (sorted(d), d)
def perm_labels(rng):
    out = {}
    for s, (pl_list, d) in famplayers.items():
        dn = pl_list[:]; rng.shuffle(dn)
        for i, p in enumerate(pl_list):
            src_lab = [(x["tier"], x["ph"]) for x in d[dn[i]]]
            for j, r in enumerate(d[p]): out[id(r)] = src_lab[j % len(src_lab)]
    return out
def eval_gridB(lab):
    out = []
    for name, fn in CELLS:
        sel = []
        for r in ROWS:
            t, ph = lab[id(r)]
            rr = dict(r); rr["tier"] = t; rr["ph"] = ph
            if fn(rr): sel.append(r)
        if len(sel) >= MINN: out.append((name, len(sel), roi(sel)))
    return out
TRUE = {id(r): (r["tier"], r["ph"]) for r in ROWS}
NPB = 400; rng = random.Random(4242)
BANDS = [(25, 60), (60, 150), (150, 400), (400, 10000)]
hi = {b: [] for b in BANDS}
for _ in range(NPB):
    g = eval_gridB(perm_labels(rng))
    for b in BANDS:
        sub = [x[2] for x in g if b[0] <= x[1] < b[1]]
        if sub: hi[b].append(max(sub))
def q(v, p):
    v = sorted(v); return v[min(len(v) - 1, int(p * len(v)))]
print("NOISE CEILING GRID B (within-family player-block label shuffle, %d perms):" % NPB)
for b in BANDS:
    if hi[b]: print("    n %-12s p95 best-cell ROI = %+.1f%%" % ("%d-%d" % b, q(hi[b], .95)))
CEILB = {b: q(hi[b], .95) for b in BANDS if hi[b]}
def band_of(n):
    for b in BANDS:
        if b[0] <= n < b[1]: return b
    return BANDS[-1]
real = eval_gridB(TRUE)
print("\n%-34s%5s%9s%19s%11s  %s" % ("cell", "n", "ROI%", "CI95", "ceiling", ""))
for name, n, rr in sorted(real, key=lambda x: -x[2]):
    sel = [r for r in ROWS if CELLD[name](r)]
    lo, h2 = ci95(sel); c = CEILB.get(band_of(n), 99)
    print("%-34s%5d%8.1f%%   [%6.1f,%6.1f]%10.1f%%  %s" % (name, n, rr, lo, h2, c, "BEATS" if rr > c else ""))

# ================================================== slate-level correlation, permutation p
print("\n" + "=" * 84)
print("SLATE-LEVEL family-vs-family PnL correlation: is the best pair beyond multiplicity?")
sl = collections.defaultdict(lambda: collections.defaultdict(list))
for r in ROWS: sl[r["src"]][r["date"]].append(r["pnl"])
fams = sorted(s for s in sl if len(sl[s]) >= 12)
def best_abs_rho(shuffled=None):
    best = 0.0; who = None
    for i, a in enumerate(fams):
        for b_ in fams[i + 1:]:
            common = sorted(set(sl[a]) & set(sl[b_]))
            if len(common) < 12: continue
            if shuffled is None:
                xs_ = [statistics.mean(sl[a][d]) for d in common]
            else:
                mp = shuffled[a]
                xs_ = [statistics.mean(sl[a][mp[d]]) for d in common]
            ys_ = [statistics.mean(sl[b_][d]) for d in common]
            r_ = pear(xs_, ys_)
            if abs(r_) > abs(best): best, who = r_, (a, b_, len(common))
    return best, who
obs, who = best_abs_rho()
print("  strongest pair: %s x %s over %d shared slates, rho=%+.3f" % (who[0], who[1], who[2], obs))
rng = random.Random(5); cnt = 0; NPS = 3000
for _ in range(NPS):
    shuf = {}
    for a in fams:
        ds = sorted(sl[a]); dd = ds[:]; rng.shuffle(dd)
        shuf[a] = dict(zip(ds, dd))
    b2, _ = best_abs_rho(shuf)
    if abs(b2) >= abs(obs): cnt += 1
print("  slate-shuffle null over ALL %d pairs: p(best |rho| >= %.3f) = %.4f"
      % (len(fams) * (len(fams) - 1) // 2, abs(obs), (cnt + 1) / (NPS + 1)))
