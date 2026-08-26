# fam_staleness.py - follow-up to fam_matrix.py.
# The one structurally interesting cell was the MIRROR of Model S gate 3 for the under
# families: "the book has NOT cut her line". This script declares a second, size-matched
# grid for it, tests the MECHANISM on raw production, checks the market-matched blind
# baseline (is a fade just the over base rate?), and quantifies cascade's coverage bias.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])

def nd(s): return (s or "").replace("-", "")[:8]
G = load("graded_bets.csv"); L = load("bets_log.csv")
li = collections.defaultdict(list)
for r in L:
    t = ts(r["captured_utc"])
    if t: li[(nd(r["date"]), (r["player"] or "").lower(), r["market"], r["side"])].append((t, r))
for v in li.values(): v.sort(key=lambda z: z[0])
bi = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None:
        bi[((b.get("player") or "").lower(), b.get("market"), b.get("side"), ln)].append((t, o))
dt2tip = collections.defaultdict(list)
for (pl, tp), row in pgrow.items(): dt2tip[(pl, row["date"])].append(tp)

BETS = []
for r in G:
    pl = (r["player"] or "").lower(); d = nd(r["date"]); mk = r["market"]; sd = r["side"]
    ln = f(r["line"]); od = f(r["odds"]); act = f(r["actual"])
    if ln is None or od is None or act is None: continue
    tps = dt2tip.get((pl, d))
    if not tps: continue
    gt = tps[0]
    if act == ln: continue
    rows = li.get((d, pl, mk, sd), []); ex = [z for z in rows if f(z[1]["line"]) == ln]
    sr = ex or rows
    T = sr[0][0] if sr else gt - datetime.timedelta(hours=12)
    opp = "Under" if sd == "Over" else "Over"
    cand = [z for z in bi.get((pl, mk, opp, ln), []) if z[0] <= gt and (gt - z[0]).total_seconds() <= 60 * 3600]
    oppod = min(cand, key=lambda z: abs((z[0] - T).total_seconds()))[1] if cand else None
    over_won = act > ln
    won = over_won if sd == "Over" else (not over_won)
    prev = prevline.get((pl, mk, gt))
    mv = None if prev is None else ln - prev
    BETS.append(dict(date=d, pl=pl, mk=mk, sd=sd, ln=ln, od=od, oppod=oppod, gt=gt, act=act,
                     won=won, over_won=over_won, src=r["src"], mv=mv,
                     tier=r.get("tier"), ev=f(sr[0][1]["ev"]) if sr else None))
TWO = [b for b in BETS if b["oppod"] is not None]

# ---------------------------------------------------------------- 1 MECHANISM, on raw production
print("=" * 100)
print("  1. MECHANISM CHECK ON RAW PRODUCTION (law 6). Does 'book did not cut her line' actually")
print("     predict she goes OVER? margin = (actual - line) / line, no prices involved.")
print("=" * 100)
def mvbuck(mv):
    if mv is None: return "n/a"
    if mv <= -0.5: return "CUT"
    if mv >= 0.5: return "RAISED"
    return "FLAT"
for fam in ("newunder", "model", "starout", "ALL-UNDERS", "overshoot", "flip_paper", "cascade"):
    if fam == "ALL-UNDERS": pool = [b for b in BETS if b["sd"] == "Under"]
    else: pool = [b for b in BETS if b["src"] == fam]
    if len(pool) < 30: continue
    out = []
    for bk in ("CUT", "FLAT", "RAISED"):
        g = [b for b in pool if mvbuck(b["mv"]) == bk]
        if len(g) < 12: out.append("%s n=%d --" % (bk, len(g))); continue
        m = [(b["act"] - b["ln"]) / b["ln"] for b in g]
        out.append("%s n=%-3d margin %+6.1f%%  over-rate %4.1f%%"
                   % (bk, len(g), 100 * statistics.mean(m), 100 * sum(1 for b in g if b["over_won"]) / len(g)))
    print("  %-11s %s" % (fam, "  |  ".join(out)))
# same thing on the WHOLE two-sided board (mega_sweep B) - the population, not our bets
print("\n  the same mechanism on the FULL BOARD (all %d two-sided quotes, not our bets):" % len(B))
for bk, sel in (("CUT", lambda r: r["linemv"] is not None and r["linemv"] <= -0.5),
                ("FLAT", lambda r: r["linemv"] is not None and -0.5 < r["linemv"] < 0.5),
                ("RAISED", lambda r: r["linemv"] is not None and r["linemv"] >= 0.5)):
    g = [r for r in B if sel(r)]
    if not g: continue
    ov = sum(1 for r in g if r["over_won"]) / len(g)
    ro = sum((r["over_od"] - 1) if r["over_won"] else -1.0 for r in g) / len(g)
    ru = sum(-1.0 if r["over_won"] else (r["under_od"] - 1) for r in g) / len(g)
    print("    %-6s n=%-5d over-rate %4.1f%%   blind Over ROI %+5.1f%%   blind Under ROI %+5.1f%%"
          % (bk, len(g), 100 * ov, 100 * ro, 100 * ru))

# ---------------------------------------------------------------- 2 declared sub-grid + ceiling
print("\n" + "=" * 100)
print("  2. DECLARED SUB-GRID: 4 families x 2 directions x 6 line-move buckets = 48 cells, min n=60")
print("=" * 100)
FAM4 = ("newunder", "overshoot", "flip_paper", "cascade")
BUCK = (("ALL", lambda b: True),
        ("CUT<=-.5", lambda b: b["mv"] is not None and b["mv"] <= -0.5),
        ("FLAT", lambda b: b["mv"] is not None and -0.5 < b["mv"] < 0.5),
        ("RAISED>=.5", lambda b: b["mv"] is not None and b["mv"] >= 0.5),
        ("notCUT", lambda b: b["mv"] is not None and b["mv"] > -0.5),
        ("notRAISED", lambda b: b["mv"] is not None and b["mv"] < 0.5))
MINN = 60
CELLS = []
for fam in FAM4:
    for dirn in ("EMIT", "FADE"):
        for bn, bf in BUCK:
            rows = [b for b in TWO if b["src"] == fam and bf(b)]
            CELLS.append(("%s %s | %s" % (fam, dirn, bn), rows, dirn))
live = [c for c in CELLS if len(c[1]) >= MINN]
print("  cells reaching n>=%d: %d of %d" % (MINN, len(live), len(CELLS)))
def roi(rows, dirn, lab):
    p = 0.0
    for b in rows:
        w = lab[id(b)]
        if dirn == "EMIT": p += (b["od"] - 1) if w else -1.0
        else: p += -1.0 if w else (b["oppod"] - 1)
    return p / len(rows)
gm_blocks = collections.defaultdict(list)
for b in TWO: gm_blocks[b["gt"]].append(b)
blocks = [v for k, v in sorted(gm_blocks.items())]
flat_all = [b for blk in blocks for b in blk]
def bperm():
    bl = list(blocks); random.shuffle(bl)
    stream = [b["won"] for blk in bl for b in blk]
    return {id(b): w for b, w in zip(flat_all, stream)}
T = 3000
sims = []
for _ in range(T):
    lab = bperm()
    sims.append(max(roi(rows, dirn, lab) for nm, rows, dirn in live))
sims.sort()
CEIL = sims[int(T * 0.95)]
print("  SUB-GRID CEILING (game-block perm, %d reps): median %+.1f%%  p95 %+.1f%%  max %+.1f%%"
      % (T, 100 * sims[T // 2], 100 * CEIL, 100 * sims[-1]))
real = {id(b): b["won"] for b in TWO}
rr = sorted(((roi(rows, dirn, real), nm, len(rows), rows, dirn) for nm, rows, dirn in live), key=lambda z: -z[0])
pv = collections.Counter()
for _ in range(T):
    lab = bperm()
    for v0, nm, n, rows, dirn in rr:
        if roi(rows, dirn, lab) >= v0: pv[nm] += 1
for v, nm, n, rows, dirn in rr:
    pn = [(((b["od"] - 1) if real[id(b)] else -1.0) if dirn == "EMIT"
           else (-1.0 if real[id(b)] else (b["oppod"] - 1))) for b in rows]
    se = statistics.pstdev(pn) / math.sqrt(len(pn))
    wr = sum(1 for b in rows if (real[id(b)] if dirn == "EMIT" else not real[id(b)])) / len(rows)
    print("  %-34s n=%-4d win %4.1f%%  ROI %+6.1f%%  CI[%+6.1f,%+6.1f]  p=%.3f%s"
          % (nm, n, 100 * wr, 100 * v, 100 * (v - 1.96 * se), 100 * (v + 1.96 * se), pv[nm] / T,
             "  <== CLEARS" if v >= CEIL else ""))

# ---------------------------------------------------------------- 3 market-matched blind baseline
print("\n" + "=" * 100)
print("  3. IS THE FADE JUST THE OVER BASE RATE? market+month-matched blind-over baseline")
print("=" * 100)
lo, hi = min(b["date"] for b in TWO), max(b["date"] for b in TWO)
bb = [r for r in B if lo <= r["date"] <= hi]
base = {}
for mk in set(r["mk"] for r in bb):
    for mo in set(r["date"][:6] for r in bb):
        g = [r for r in bb if r["mk"] == mk and r["date"][:6] == mo]
        if g:
            base[(mk, mo, "Over")] = sum((r["over_od"] - 1) if r["over_won"] else -1.0 for r in g) / len(g)
            base[(mk, mo, "Under")] = sum(-1.0 if r["over_won"] else (r["under_od"] - 1) for r in g) / len(g)
def alpha(rows, dirn):
    tot = 0.0; k = 0
    for b in rows:
        s = ("Under" if b["sd"] == "Over" else "Over") if dirn == "FADE" else b["sd"]
        bl = base.get((b["mk"], b["date"][:6], s))
        if bl is None: continue
        w = b["won"] if dirn == "EMIT" else (not b["won"])
        pn = ((b["od"] - 1) if w else -1.0) if dirn == "EMIT" else ((b["oppod"] - 1) if w else -1.0)
        tot += pn - bl; k += 1
    return (tot / k, k) if k else (None, 0)
for nm, rows, dirn in live:
    a, k = alpha(rows, dirn)
    if a is None: continue
    print("  %-34s n=%-4d ALPHA over matched blind %+6.1f%%" % (nm, k, 100 * a))

# ---------------------------------------------------------------- 4 stability + cascade bias
print("\n" + "=" * 100)
print("  4. STABILITY BY MONTH, and cascade's coverage confound")
print("=" * 100)
for nm, rows, dirn in live:
    if "newunder" not in nm: continue
    out = []
    for mo in ("202606", "202607", "202608"):
        g = [b for b in rows if b["date"][:6] == mo]
        if len(g) < 15: out.append("%s n=%d --" % (mo[4:], len(g))); continue
        v = roi(g, dirn, real)
        out.append("%s n=%-3d %+6.1f%%" % (mo[4:], len(g), 100 * v))
    print("  %-34s %s" % (nm, "  ".join(out)))
allc = [b for b in BETS if b["src"] == "cascade"]
hasq = [b for b in allc if b["oppod"] is not None]; noq = [b for b in allc if b["oppod"] is None]
e1 = sum((b["od"] - 1) if b["won"] else -1.0 for b in hasq) / len(hasq)
e2 = sum((b["od"] - 1) if b["won"] else -1.0 for b in noq) / len(noq)
print("\n  cascade as-emitted: WITH a real opposite quote n=%d ROI %+.1f%% | WITHOUT n=%d ROI %+.1f%%"
      % (len(hasq), 100 * e1, len(noq), 100 * e2))
print("  win rate with-quote %.1f%%  without-quote %.1f%%"
      % (100 * sum(1 for b in hasq if b["won"]) / len(hasq), 100 * sum(1 for b in noq if b["won"]) / len(noq)))
print("  -> the fade of cascade can only be priced on 24%% of its bets, and that 24%% is the")
print("     half that lost. Any cascade FADE number is a coverage artifact, not a result.")

# ---------------------------------------------------------------- 5 small families, for the record
print("\n" + "=" * 100)
print("  5. FAMILIES UNDER n=40 on the two-sided sample - reported, not tested")
print("=" * 100)
for fam in ("flip", "model", "hotover", "starout"):
    a = [b for b in TWO if b["src"] == fam]
    if not a: continue
    e = sum((b["od"] - 1) if b["won"] else -1.0 for b in a) / len(a)
    fd = sum(-1.0 if b["won"] else (b["oppod"] - 1) for b in a) / len(a)
    pn = [((b["od"] - 1) if b["won"] else -1.0) for b in a]
    se = statistics.pstdev(pn) / math.sqrt(len(a))
    print("  %-9s n=%-3d EMIT %+6.1f%% CI[%+6.1f,%+6.1f]   FADE %+6.1f%%"
          % (fam, len(a), 100 * e, 100 * (e - 1.96 * se), 100 * (e + 1.96 * se), 100 * fd))
