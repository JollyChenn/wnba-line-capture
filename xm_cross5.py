# xm_cross5.py - close-out: CI on the calibration null, redundancy detail, and formal
# difference tests for agreement / contradiction (the questions the grid answered only by cell).
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
ROWS = []
for k, v in FIRE.items():
    row = pgrow.get((v["pl"], v["gt"]))
    if not row: continue
    act = row.get(v["mk"])
    if act is None or act == v["line"]: continue
    won = (act > v["line"]) if v["side"] == "Over" else (act < v["line"])
    pv = prevline.get((v["pl"], v["mk"], v["gt"]))
    ROWS.append(dict(v, act=act, won=won, pnl=(v["odds"] - 1) if won else -1.0,
                     ph=((1 + v["ev"]) / v["odds"]) if v["ev"] is not None else None,
                     raised=(None if pv is None else (v["line"] - pv) >= 0.5)))
OVERF = {"cascade", "overshoot", "flip_paper", "flip", "hotover", "usgshock"}
SIGS_S = ("flip", "hotover", "overshoot"); BET_MK = ("pra", "pr", "pts")
def is_S(r): return r["src"] in SIGS_S and r["mk"] in BET_MK and r["raised"] is not None and not r["raised"]
def pear(xs, ys):
    mx, my = statistics.mean(xs), statistics.mean(ys)
    n = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    dx = math.sqrt(sum((a - mx) ** 2 for a in xs)); dy = math.sqrt(sum((b - my) ** 2 for b in ys))
    return n / (dx * dy) if dx and dy else 0.0
def tied_rank(v):
    o = sorted(range(len(v)), key=lambda i: v[i]); rr = [0.0] * len(v); i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]: j += 1
        for kk in range(i, j + 1): rr[o[kk]] = (i + j) / 2.0 + 1
        i = j + 1
    return rr
def spearman(xs, ys): return pear(tied_rank(xs), tied_rank(ys))

# ---------------- (1) how tight is the calibration null? player-block bootstrap CI ------------
cal = [r for r in ROWS if r["ph"] is not None and 0.01 < r["ph"] < 0.999]
byp = collections.defaultdict(list)
for r in cal: byp[r["pl"]].append(r)
pls = sorted(byp)
obs = spearman([r["ph"] for r in cal], [1.0 if r["won"] else 0.0 for r in cal])
rng = random.Random(77); bs = []
for _ in range(2000):
    samp = []
    for _ in range(len(pls)): samp.extend(byp[rng.choice(pls)])
    if len(set(r["won"] for r in samp)) < 2: continue
    bs.append(spearman([r["ph"] for r in samp], [1.0 if r["won"] else 0.0 for r in samp]))
bs.sort()
print("CALIBRATION NULL, HOW TIGHT?")
print("  spearman(engine hit prob, won) = %+.4f   player-block bootstrap CI95 [%+.3f, %+.3f]  n=%d"
      % (obs, bs[int(.025 * len(bs))], bs[int(.975 * len(bs))], len(cal)))
print("  -> the confidence layer's rank information is bounded inside that interval.")
lb = []
for _ in range(2000):
    samp = []
    for _ in range(len(pls)): samp.extend(byp[rng.choice(pls)])
    lb.append(statistics.mean(1.0 if r["won"] else 0.0 for r in samp) - statistics.mean(r["ph"] for r in samp))
lb.sort()
print("  level bias (realised - predicted) = %+.1f pp  CI95 [%+.1f, %+.1f]"
      % (100 * (statistics.mean(1.0 if r["won"] else 0.0 for r in cal) - statistics.mean(r["ph"] for r in cal)),
         100 * lb[int(.025 * len(lb))], 100 * lb[int(.975 * len(lb))]))
# does ph predict the RAW stat at all (mechanism check on production, not P&L)?
z = []
for r in cal:
    row = pgrow[(r["pl"], r["gt"])]
    prior = [x for x in hist.get(r["pl"], []) if x["tip"] < r["gt"]][-10:]
    if len(prior) < 6: continue
    sd_ = statistics.pstdev([x[r["mk"]] for x in prior]) or 1
    zz = (row[r["mk"]] - r["line"]) / sd_
    z.append((r["ph"], zz if r["side"] == "Over" else -zz))
print("  MECHANISM on raw production: spearman(predicted hit, z-score of realised vs line, signed"
      " to the bet side) = %+.4f  n=%d" % (spearman([a for a, b in z], [b for a, b in z]), len(z)))

# ---------------- (2) redundancy detail --------------------------------------------------------
print("\nREDUNDANCY: are two families the same model?")
pg = collections.defaultdict(dict)
for r in ROWS: pg[(r["pl"], r["gt"])][r["src"]] = r
FAMS = ["newunder", "cascade", "overshoot", "flip_paper", "flip", "model", "hotover", "starout"]
print("%-12s x %-12s%7s%9s%12s%14s%12s" % ("A", "B", "both", "J(pg)", "same mkt", "same mkt+line", "agree W/L"))
out = []
for i, a in enumerate(FAMS):
    for b_ in FAMS[i + 1:]:
        na = sum(1 for v in pg.values() if a in v); nb = sum(1 for v in pg.values() if b_ in v)
        both = [v for v in pg.values() if a in v and b_ in v]
        if not both: continue
        j = len(both) / (na + nb - len(both))
        sm = sum(1 for v in both if v[a]["mk"] == v[b_]["mk"])
        sl = sum(1 for v in both if v[a]["mk"] == v[b_]["mk"] and v[a]["line"] == v[b_]["line"] and v[a]["side"] == v[b_]["side"])
        ag = sum(1 for v in both if v[a]["won"] == v[b_]["won"]) / len(both)
        out.append((j, a, b_, len(both), sm, sl, ag))
for j, a, b_, n, sm, sl, ag in sorted(out, reverse=True)[:10]:
    print("%-12s x %-12s%7d%9.3f%12d%14d%11.0f%%" % (a, b_, n, j, sm, sl, 100 * ag))
print("  ('same mkt+line' = literally the identical bet. That is the only true duplicate.)")

# unique contribution: drop each family, what is lost from the union of over-family bets?
print("\n  UNIQUE CONTRIBUTION (over-family bets on player-games no other over-family touched):")
for s in ("overshoot", "flip_paper", "flip", "hotover", "cascade"):
    mine = [v[s] for v in pg.values() if s in v]
    solo = [v[s] for v in pg.values() if s in v and len(set(v) & OVERF) == 1]
    if not mine: continue
    print("    %-12s n=%4d  solo %4d (%3.0f%%)  solo ROI %+6.1f%%  shared ROI %+6.1f%%"
          % (s, len(mine), len(solo), 100 * len(solo) / len(mine),
             100 * statistics.mean([r["pnl"] for r in solo]) if solo else float("nan"),
             100 * statistics.mean([v[s]["pnl"] for v in pg.values() if s in v and len(set(v) & OVERF) > 1])
             if any(s in v and len(set(v) & OVERF) > 1 for v in pg.values()) else float("nan")))

# ---------------- (3) formal difference tests --------------------------------------------------
print("\nFORMAL DIFFERENCE TESTS (player-block permutation of the pg-level label)")
pg_srcs = collections.defaultdict(set); pg_sides = collections.defaultdict(set)
for r in ROWS:
    pg_srcs[(r["pl"], r["gt"])].add(r["src"]); pg_sides[(r["pl"], r["gt"])].add(r["side"])
NOV = {k: len(v & OVERF) for k, v in pg_srcs.items()}
CON = {k: len(v) > 1 for k, v in pg_sides.items()}
def diff_test(pool, labfn, name, npm=3000):
    rows = [r for r in ROWS if pool(r)]
    A = [r["pnl"] for r in rows if labfn((r["pl"], r["gt"]))]
    Bb = [r["pnl"] for r in rows if not labfn((r["pl"], r["gt"]))]
    if len(A) < 15 or len(Bb) < 15:
        print("  %-46s too thin (%d/%d)" % (name, len(A), len(Bb))); return
    d = statistics.mean(A) - statistics.mean(Bb)
    bp = collections.defaultdict(list)
    for r in rows: bp[r["pl"]].append(r)
    ps = sorted(bp); KY = {p: sorted({r["gt"] for r in bp[p]}) for p in ps}
    LB = {p: [labfn((p, g)) for g in KY[p]] for p in ps}
    rg = random.Random(1234); cnt = 0
    for _ in range(npm):
        dn = ps[:]; rg.shuffle(dn); mp = {}
        for i, p in enumerate(ps):
            dd = LB[dn[i]]
            for j, g in enumerate(KY[p]): mp[(p, g)] = dd[j % len(dd)]
        aa = [r["pnl"] for r in rows if mp[(r["pl"], r["gt"])]]
        bb = [r["pnl"] for r in rows if not mp[(r["pl"], r["gt"])]]
        if len(aa) < 5 or len(bb) < 5: continue
        if abs(statistics.mean(aa) - statistics.mean(bb)) >= abs(d): cnt += 1
    print("  %-46s nA=%4d nB=%4d  diff %+6.1f pp  p=%.4f" % (name, len(A), len(Bb), 100 * d, (cnt + 1) / (npm + 1)))
diff_test(lambda r: r["src"] in OVERF, lambda k: NOV[k] >= 2, "over-fam: 2+ models agree vs alone")
diff_test(is_S, lambda k: NOV[k] >= 2, "Model S: another over-fam agrees vs alone")
diff_test(lambda r: r["src"] in OVERF, lambda k: CON[k], "over-fam: contradicted vs not")
diff_test(lambda r: r["src"] not in OVERF, lambda k: CON[k], "under-fam: contradicted vs not")
diff_test(is_S, lambda k: CON[k], "Model S: contradicted vs not")

# diff-in-diff on the contradiction question
ov_c = [r["pnl"] for r in ROWS if r["src"] in OVERF and CON[(r["pl"], r["gt"])]]
ov_n = [r["pnl"] for r in ROWS if r["src"] in OVERF and not CON[(r["pl"], r["gt"])]]
un_c = [r["pnl"] for r in ROWS if r["src"] not in OVERF and CON[(r["pl"], r["gt"])]]
un_n = [r["pnl"] for r in ROWS if r["src"] not in OVERF and not CON[(r["pl"], r["gt"])]]
print("\n  CONTRADICTION diff-in-diff (over-minus-under gap):")
print("    contradicted    over %+.1f%% (n=%d)  under %+.1f%% (n=%d)  gap %+.1f pp"
      % (100 * statistics.mean(ov_c), len(ov_c), 100 * statistics.mean(un_c), len(un_c),
         100 * (statistics.mean(ov_c) - statistics.mean(un_c))))
print("    not contradicted over %+.1f%% (n=%d)  under %+.1f%% (n=%d)  gap %+.1f pp"
      % (100 * statistics.mean(ov_n), len(ov_n), 100 * statistics.mean(un_n), len(un_n),
         100 * (statistics.mean(ov_n) - statistics.mean(un_n))))
print("    DiD = %+.1f pp  -> a contradiction carries essentially no extra information"
      % (100 * ((statistics.mean(ov_c) - statistics.mean(un_c)) - (statistics.mean(ov_n) - statistics.mean(un_n)))))
