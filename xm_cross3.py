# xm_cross3.py - (a) stress the "3+ models agree" fade cell with cluster-aware nulls
#                (b) same-slate / same-game outcome correlation (staking)
#                (c) calibration of the engine's own hit-probability, pooled across families
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
                     raised=(None if pv is None else (v["line"] - pv) >= 0.5)))
pg_srcs = collections.defaultdict(set)
for r in ROWS: pg_srcs[(r["pl"], r["gt"])].add(r["src"])
OVERF = {"cascade", "overshoot", "flip_paper", "flip", "hotover", "usgshock"}
UNDERF = {"newunder", "model", "starout", "fragile"}
NOV = {k: len(v & OVERF) for k, v in pg_srcs.items()}

def roi(p): return 100 * statistics.mean(p) if p else float("nan")

# ============================================================ (a) the 3+ crowd, stressed
print("=" * 84)
print("(a) FADE CELL STRESS: over-family bet on a player-game where 3+ over-families fired")
OV_ROWS = [r for r in ROWS if r["src"] in OVERF]
def lab(r): return NOV[(r["pl"], r["gt"])]
cell = [r for r in OV_ROWS if lab(r) >= 3]
print("  n fires=%d  distinct player-games=%d  distinct games=%d  distinct players=%d  slates=%d"
      % (len(cell), len(set((r["pl"], r["gt"]) for r in cell)), len(set(r["gid"] for r in cell)),
         len(set(r["pl"] for r in cell)), len(set(r["date"] for r in cell))))
obs = roi([r["pnl"] for r in cell])
print("  observed ROI %+.1f%%" % obs)
# per player-game mean, so one crowded game cannot vote 5 times
pgm = collections.defaultdict(list)
for r in cell: pgm[(r["pl"], r["gt"])].append(r["pnl"])
pgmeans = [statistics.mean(v) for v in pgm.values()]
m = statistics.mean(pgmeans); sd = statistics.pstdev(pgmeans)
h = 1.96 * sd / math.sqrt(len(pgmeans))
print("  CLUSTERED (one vote per player-game): n=%d  ROI %+.1f%%  CI[%+.1f,%+.1f]"
      % (len(pgmeans), 100 * m, 100 * (m - h), 100 * (m + h)))

# null 1: shuffle the crowd label across player-games, blocked by PLAYER
byp = collections.defaultdict(list)
for r in OV_ROWS: byp[r["pl"]].append(r)
players = sorted(byp)
PGKEYS = {p: sorted({r["gt"] for r in byp[p]}) for p in players}
PGLAB = {p: [NOV[(p, g)] for g in PGKEYS[p]] for p in players}
def nullA(rng):
    donors = players[:]; rng.shuffle(donors); out = {}
    for i, p in enumerate(players):
        d = PGLAB[donors[i]]
        for j, g in enumerate(PGKEYS[p]): out[(p, g)] = d[j % len(d)]
    return out
# null 2: relabel GAMES - the crowd is partly a game-level phenomenon (star out -> whole team)
gm = collections.defaultdict(set)
for r in OV_ROWS: gm[r["gid"]].add((r["pl"], r["gt"]))
games = sorted(g for g in gm if g)
def nullB(rng):
    donors = games[:]; rng.shuffle(donors); out = {}
    for i, g in enumerate(games):
        src_pgs = sorted(gm[donors[i]]); tgt = sorted(gm[g])
        labs = [NOV[k] for k in src_pgs]
        for j, k in enumerate(tgt): out[k] = labs[j % len(labs)]
    return out
for nm, fn in (("player-block", nullA), ("GAME-block", nullB)):
    rng = random.Random(7); cnt = 0; tot = 0; szs = []; cls = []
    for _ in range(3000):
        lb = fn(rng)
        sel = [r for r in OV_ROWS if lb.get((r["pl"], r["gt"]), 0) >= 3]
        if len(sel) < 20: continue
        tot += 1; szs.append(len(sel)); cls.append(len(set((r["pl"], r["gt"]) for r in sel)))
        if roi([r["pnl"] for r in sel]) <= obs: cnt += 1
    print("  null %-14s p(ROI<=%.1f%%)=%.4f   (perm cells: mean n=%.0f, mean clusters=%.1f)"
          % (nm, obs, (cnt + 1) / (tot + 1), statistics.mean(szs), statistics.mean(cls)))

# out-of-sample split by date
cut = sorted(set(r["date"] for r in cell))[len(set(r["date"] for r in cell)) // 2]
e = [r["pnl"] for r in cell if r["date"] < cut]; l = [r["pnl"] for r in cell if r["date"] >= cut]
print("  time split at %s:  early n=%d ROI %+.1f%%   late n=%d ROI %+.1f%%"
      % (cut, len(e), roi(e), len(l), roi(l)))
# and the fade actually bettable? the mirror UNDER at the same line, real two-sided price
mir = []
for r in cell:
    sd_ = side.get((r["pl"], r["mk"], r["gt"]), {})
    if "Under" not in sd_ or "Over" not in sd_: continue
    if sd_["Over"][1] != sd_["Under"][1]: continue
    ln = sd_["Under"][1]; od = sd_["Under"][2]
    a = pgrow[(r["pl"], r["gt"])][r["mk"]]
    if a == ln: continue
    mir.append((od - 1) if a < ln else -1.0)
print("  MIRROR (bet the UNDER at the board's real under price, same line): n=%d ROI %+.1f%%"
      % (len(mir), roi(mir)))

# ============================================================ (b) outcome correlation
print("\n" + "=" * 84)
print("(b) OUTCOME CORRELATION - does one family's win predict another's on the same night?")
def phi(pairs):
    if len(pairs) < 30: return None, len(pairs)
    xs = [p[0] for p in pairs]; ys = [p[1] for p in pairs]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((a - mx) * (b - my) for a, b in pairs)
    dx = math.sqrt(sum((a - mx) ** 2 for a in xs)); dy = math.sqrt(sum((b - my) ** 2 for b in ys))
    return (num / (dx * dy) if dx and dy else None), len(pairs)
same_game, same_slate_diff_game, diff_slate = [], [], []
bydate = collections.defaultdict(list)
for r in ROWS: bydate[r["date"]].append(r)
for d, rs in bydate.items():
    for i in range(len(rs)):
        for j in range(i + 1, len(rs)):
            a, b_ = rs[i], rs[j]
            if a["src"] == b_["src"]: continue
            if a["pl"] == b_["pl"]: continue          # same player = trivially linked
            v = (1.0 if a["won"] else 0.0, 1.0 if b_["won"] else 0.0)
            (same_game if a["gid"] == b_["gid"] else same_slate_diff_game).append(v)
dates = sorted(bydate)
rng = random.Random(3)
for _ in range(60000):
    d1, d2 = rng.sample(dates, 2)
    a = rng.choice(bydate[d1]); b_ = rng.choice(bydate[d2])
    if a["src"] == b_["src"]: continue
    diff_slate.append((1.0 if a["won"] else 0.0, 1.0 if b_["won"] else 0.0))
for nm, v in (("SAME GAME, diff family", same_game),
              ("same slate, DIFF game", same_slate_diff_game),
              ("different slates (control)", diff_slate)):
    r_, n = phi(v)
    print("  %-28s pairs=%6d  corr(win_a, win_b) = %s" % (nm, n, ("%+.3f" % r_) if r_ is not None else "n/a"))
# per-family-pair, same slate
print("\n  per-family-pair, SAME SLATE (all pairs of bets, different players):")
pp = collections.defaultdict(list)
for d, rs in bydate.items():
    for i in range(len(rs)):
        for j in range(i + 1, len(rs)):
            a, b_ = rs[i], rs[j]
            if a["pl"] == b_["pl"]: continue
            key = tuple(sorted((a["src"], b_["src"])))
            pp[key].append((1.0 if a["won"] else 0.0, 1.0 if b_["won"] else 0.0))
out = []
for k, v in pp.items():
    r_, n = phi(v)
    if r_ is not None and n >= 200: out.append((abs(r_), r_, k, n))
for _, r_, k, n in sorted(out, reverse=True)[:12]:
    print("    %-24s pairs=%6d  rho=%+.3f" % (" x ".join(k), n, r_))
# slate-level aggregate: mean pnl per family per slate, correlate across slates
print("\n  slate-level mean-PnL correlation (matters for bankroll swings):")
sl = collections.defaultdict(lambda: collections.defaultdict(list))
for r in ROWS: sl[r["src"]][r["date"]].append(r["pnl"])
fams = [s for s in sl if len(sl[s]) >= 12]
def pear(xs, ys):
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    dx = math.sqrt(sum((a - mx) ** 2 for a in xs)); dy = math.sqrt(sum((b - my) ** 2 for b in ys))
    return num / (dx * dy) if dx and dy else None
res = []
for i, a in enumerate(sorted(fams)):
    for b_ in sorted(fams)[i + 1:]:
        common = sorted(set(sl[a]) & set(sl[b_]))
        if len(common) < 12: continue
        xs = [statistics.mean(sl[a][d]) for d in common]; ys = [statistics.mean(sl[b_][d]) for d in common]
        r_ = pear(xs, ys)
        if r_ is not None: res.append((abs(r_), r_, a, b_, len(common)))
for _, r_, a, b_, n in sorted(res, reverse=True):
    t = r_ * math.sqrt((n - 2) / max(1e-9, 1 - r_ * r_))
    print("    %-12s x %-12s slates=%3d  rho=%+.3f  t=%+.2f" % (a, b_, n, r_, t))

# ============================================================ (c) calibration
print("\n" + "=" * 84)
print("(c) THE CONFIDENCE LAYER - engine hit prob = (1+ev)/odds, pooled across ALL families")
cal = [r for r in ROWS if r["ev"] is not None and r["odds"]]
for r in cal: r["ph"] = (1 + r["ev"]) / r["odds"]
cal = [r for r in cal if 0.01 < r["ph"] < 0.999]
print("  n with usable ev: %d of %d" % (len(cal), len(ROWS)))
cal.sort(key=lambda r: r["ph"])
NB = 8; per = max(1, len(cal) // NB)
print("\n  %-16s%6s%12s%12s%10s%10s" % ("predicted band", "n", "pred hit", "real hit", "gap", "ROI%"))
for i in range(NB):
    ch = cal[i * per:(i + 1) * per] if i < NB - 1 else cal[i * per:]
    if len(ch) < 15: continue
    pr = statistics.mean(r["ph"] for r in ch); ac = statistics.mean(1.0 if r["won"] else 0.0 for r in ch)
    print("  %-16s%6d%11.1f%%%11.1f%%%9.1f%%%9.1f%%" % (
        "%.2f-%.2f" % (ch[0]["ph"], ch[-1]["ph"]), len(ch), 100 * pr, 100 * ac,
        100 * (ac - pr), roi([r["pnl"] for r in ch])))
# overall
pr = statistics.mean(r["ph"] for r in cal); ac = statistics.mean(1.0 if r["won"] else 0.0 for r in cal)
print("  %-16s%6d%11.1f%%%11.1f%%%9.1f%%%9.1f%%" % ("ALL", len(cal), 100 * pr, 100 * ac,
      100 * (ac - pr), roi([r["pnl"] for r in cal])))
# rank correlation predicted vs realised, player-blocked p
def spearman(xs, ys):
    def rk(v):
        o = sorted(range(len(v)), key=lambda i: v[i]); rr = [0] * len(v)
        for i, idx in enumerate(o): rr[idx] = i
        return rr
    return pear(rk(xs), rk(ys))
xs = [r["ph"] for r in cal]; ys = [1.0 if r["won"] else 0.0 for r in cal]
rho = spearman(xs, ys)
byp2 = collections.defaultdict(list)
for r in cal: byp2[r["pl"]].append(r)
pls = sorted(byp2)
rng = random.Random(11); cnt = 0
for _ in range(2000):
    dn = pls[:]; rng.shuffle(dn)
    xx = []
    for i, p in enumerate(pls):
        d = [r["ph"] for r in byp2[dn[i]]]
        for j in range(len(byp2[p])): xx.append(d[j % len(d)])
    yy = [1.0 if r["won"] else 0.0 for p in pls for r in byp2[p]]
    if abs(spearman(xx, yy)) >= abs(rho): cnt += 1
print("  spearman(predicted hit, won) = %+.4f   player-block p = %.4f" % (rho, (cnt + 1) / 2001))
# tier
print("\n  by TIER (engine's own label):")
tb = collections.defaultdict(list)
for r in ROWS: tb[r["tier"] or "?"].append(r)
for t in sorted(tb, key=lambda t: -len(tb[t])):
    v = tb[t]
    if len(v) < 20: continue
    ph = [((1 + r["ev"]) / r["odds"]) for r in v if r["ev"] is not None and r["odds"]]
    print("    %-8s n=%4d  pred %5.1f%%  real %5.1f%%  ROI %+6.1f%%" % (
        t, len(v), 100 * statistics.mean(ph) if ph else float("nan"),
        100 * statistics.mean(1.0 if r["won"] else 0.0 for r in v), roi([r["pnl"] for r in v])))
print("\n  by TIER within OVER-families only (removes the family/side confound):")
for t in sorted(tb, key=lambda t: -len(tb[t])):
    v = [r for r in tb[t] if r["src"] in OVERF]
    if len(v) < 20: continue
    print("    %-8s n=%4d  real %5.1f%%  ROI %+6.1f%%" % (
        t, len(v), 100 * statistics.mean(1.0 if r["won"] else 0.0 for r in v), roi([r["pnl"] for r in v])))
