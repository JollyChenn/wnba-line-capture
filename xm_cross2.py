# xm_cross2.py - size-stratified ceiling AND floor, plus the mechanism test for the
# "many models agree -> worse" inversion, plus same-slate outcome correlation.
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

pg_srcs = collections.defaultdict(set); pg_sides = collections.defaultdict(set)
pgm_srcs = collections.defaultdict(set)
for r in ROWS:
    pg_srcs[(r["pl"], r["gt"])].add(r["src"]); pg_sides[(r["pl"], r["gt"])].add(r["side"])
    pgm_srcs[(r["pl"], r["mk"], r["gt"])].add(r["src"])
OVERF = {"cascade", "overshoot", "flip_paper", "flip", "hotover", "usgshock"}
UNDERF = {"newunder", "model", "starout", "fragile"}
BUND = {}
for r in ROWS:
    s = pg_srcs[(r["pl"], r["gt"])]; sm = pgm_srcs[(r["pl"], r["mk"], r["gt"])]
    BUND[(r["pl"], r["gt"], r["mk"])] = dict(srcs=frozenset(s), srcs_mk=frozenset(sm),
        n_over=len(s & OVERF), n_under=len(s & UNDERF), n_all=len(s),
        contra=(len(pg_sides[(r["pl"], r["gt"])]) > 1))

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
CELLD = dict(CELLS); MINN = 25
def roi(rows): return 100 * statistics.mean([r["pnl"] for r in rows]) if rows else None

byplayer = collections.defaultdict(list)
for r in ROWS: byplayer[r["pl"]].append(r)
players = sorted(byplayer)
KEYS = {p: sorted({(r["gt"], r["mk"]) for r in byplayer[p]}) for p in players}
SEQ = {p: [BUND[(p, gt, mk)] for gt, mk in KEYS[p]] for p in players}
def perm_bundles(rng):
    donors = players[:]; rng.shuffle(donors); out = {}
    for i, p in enumerate(players):
        d = SEQ[donors[i]]
        for j, (gt, mk) in enumerate(KEYS[p]): out[(p, gt, mk)] = d[j % len(d)]
    return out

# ---- size-stratified ceiling AND floor -------------------------------------------------------
BANDS = [(25, 60), (60, 150), (150, 400), (400, 10000)]
def eval_grid(bmap):
    out = []
    for name, fn in CELLS:
        sel = [r for r in ROWS if fn(r, bmap[(r["pl"], r["gt"], r["mk"])])]
        if len(sel) >= MINN: out.append((name, len(sel), roi(sel)))
    return out
NP = 500; rng = random.Random(20260826)
hi_band = {b: [] for b in BANDS}; lo_band = {b: [] for b in BANDS}
allhi, alllo = [], []
for _ in range(NP):
    g = eval_grid(perm_bundles(rng))
    if not g: continue
    allhi.append(max(x[2] for x in g)); alllo.append(min(x[2] for x in g))
    for b in BANDS:
        sub = [x[2] for x in g if b[0] <= x[1] < b[1]]
        if sub: hi_band[b].append(max(sub)); lo_band[b].append(min(sub))
def q(v, p):
    v = sorted(v); return v[min(len(v) - 1, int(p * len(v)))]
print("NOISE CEILING / FLOOR by cell size (player-block relabel, %d perms, 42-cell grid)" % NP)
print("%-16s%8s%10s%10s" % ("cell size", "perms", "p95 hi", "p5 lo"))
print("%-16s%8d%9.1f%%%9.1f%%" % ("ALL", len(allhi), q(allhi, .95), q(alllo, .05)))
for b in BANDS:
    if hi_band[b]:
        print("%-16s%8d%9.1f%%%9.1f%%" % ("n %d-%d" % b, len(hi_band[b]), q(hi_band[b], .95), q(lo_band[b], .05)))
CEIL = {b: (q(hi_band[b], .95), q(lo_band[b], .05)) for b in BANDS if hi_band[b]}
def band_of(n):
    for b in BANDS:
        if b[0] <= n < b[1]: return b
    return BANDS[-1]

real = eval_grid(BUND)
print("\n%-46s%5s%9s%12s%12s  %s" % ("cell", "n", "ROI%", "band-hi", "band-lo", "verdict"))
for name, n, rr in sorted(real, key=lambda x: -x[2]):
    b = band_of(n); h, lo = CEIL.get(b, (99, -99))
    v = "BEATS-HI" if rr > h else ("BEATS-LO(fade)" if rr < lo else "")
    print("%-46s%5d%8.1f%%%11.1f%%%11.1f%%  %s" % (name, n, rr, h, lo, v))

# ---- MECHANISM: does a crowded player-game actually under-produce vs her line? ---------------
print("\n=== MECHANISM TEST on RAW PRODUCTION (all board quotes, not just our bets) ===")
print("story to test: when 3+ of our over-models pile onto one player-game, is her realised")
print("stat actually LOWER vs the line than when 1 model fires?  (if not, the -43% cell is noise)")
nover_of = {}
for (pl, gt), s in pg_srcs.items(): nover_of[(pl, gt)] = len(s & OVERF)
buck = collections.defaultdict(list)
for r in B:                                     # B = the full two-sided board, mega_sweep
    k = (r["pl"], r["gt"])
    n = nover_of.get(k, 0)
    lab = "0 (no model fired)" if n == 0 else ("1" if n == 1 else ("2" if n == 2 else "3+"))
    z = (r["medgap"])                            # trailing median minus line: how generous the line is
    buck[lab].append((1.0 if r["over_won"] else 0.0, z, r["line"]))
print("%-20s%7s%12s%14s" % ("over-models fired", "n", "over-rate", "median-gap"))
for lab in ("0 (no model fired)", "1", "2", "3+"):
    v = buck.get(lab, [])
    if not v: continue
    print("%-20s%7d%11.1f%%%13.2f" % (lab, len(v), 100 * statistics.mean(x[0] for x in v),
                                      statistics.mean(x[1] for x in v)))
# same, restricted to the exact markets our over-models bet
print("\n  restricted to pra/pr/pts only:")
buck2 = collections.defaultdict(list)
for r in B:
    if r["mk"] not in ("pra", "pr", "pts"): continue
    n = nover_of.get((r["pl"], r["gt"]), 0)
    lab = "0" if n == 0 else ("1" if n == 1 else ("2" if n == 2 else "3+"))
    buck2[lab].append((1.0 if r["over_won"] else 0.0, r["medgap"]))
for lab in ("0", "1", "2", "3+"):
    v = buck2.get(lab, [])
    if not v: continue
    print("  %-18s%7d%11.1f%%%13.2f" % (lab, len(v), 100 * statistics.mean(x[0] for x in v),
                                        statistics.mean(x[1] for x in v)))

# ---- what IS a 3+ crowd? -----------------------------------------------------------------------
crowd = [r for r in ROWS if r["src"] in OVERF and BUND[(r["pl"], r["gt"], r["mk"])]["n_over"] >= 3]
print("\n3+-crowd fires: %d, on %d player-games, %d distinct players"
      % (len(crowd), len(set((r["pl"], r["gt"]) for r in crowd)), len(set(r["pl"] for r in crowd))))
print("  src mix:", dict(collections.Counter(r["src"] for r in crowd)))
print("  top players:", collections.Counter(r["pl"] for r in crowd).most_common(6))
print("  slates:", len(set(r["date"] for r in crowd)),
      " top slates:", collections.Counter(r["date"] for r in crowd).most_common(4))
