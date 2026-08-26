# C2 sharp gap, C3 game-total gradient, C4 volatility gradient -- same bar as C1.
import platform; platform._wmi = None
import os, sys, json, math, random, statistics, collections
import numpy as np
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, D)
from t4_lib import base, boot_ci_by_game, drawdown, longest_losing
R = base()
SIGS = ("flip", "hotover", "overshoot"); BM = ("pra", "pr", "pts")
LOG = []; PV = {}
def P(s=""):
    print(s); LOG.append(s)
def spear(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    rx = np.argsort(np.argsort(x)).astype(float); ry = np.argsort(np.argsort(y)).astype(float)
    rx -= rx.mean(); ry -= ry.mean()
    return float((rx@ry)/math.sqrt((rx@rx)*(ry@ry)))
rng = np.random.default_rng(20260826)

# ============================================================== C2
P("="*100)
P("C2  SHARP GAP  --  bet toward Pinnacle when 1xbet's player line differs by >= 1 pt")
P("="*100)
S = [r for r in R if r["sharp"] is not None]
for r in S: r["gap"] = round(r["sharp"] - r["line"], 2)
P("  COVERAGE FIRST. A sharp line exists for %d of %d board quotes (%.1f%%), %d games." % (
    len(S), len(R), 100*len(S)/len(R), len(set(r["gt"] for r in S))))
P("  by month: " + "  ".join("%s n=%d" % (m, c) for m, c in
                             sorted(collections.Counter(r["date"][:6] for r in S).items())))
P("  pinn_board.csv (a real board sweep) only exists from 2026-08-21. Everything before that")
P("  is the pinn column of bets_log.csv, i.e. ONLY players the engine had already flagged.")
P("  So the pre-August-21 half of C2's sample is conditioned on the engine's own attention.")
bets = []
for r in S:
    if abs(r["gap"]) < 1.0: continue
    side = "over" if r["gap"] > 0 else "under"      # follow Pinnacle
    if r["actual"] == r["line"]: w = None
    else: w = (r["actual"] > r["line"]) if side == "over" else (r["actual"] < r["line"])
    pr = r["over"] if side == "over" else r["under"]
    bets.append(dict(g=r["gt"], date=r["date"], pl=r["pl"], mk=r["mk"], tm=r["tm"],
                     price=pr, won=w, gap=r["gap"], side=side, row=r))
def summ(b):
    if not b: return dict(n=0, roi=0.0, wr=0.0, g=0, w=0)
    tot = sum(0.0 if x["won"] is None else ((x["price"]-1) if x["won"] else -1.0) for x in b)
    dec = [x for x in b if x["won"] is not None]
    w = sum(1 for x in dec if x["won"])
    return dict(n=len(b), roi=tot/len(b), wr=w/max(len(dec), 1), g=len(set(x["g"] for x in b)), w=w, u=tot)
s = summ(bets)
lo, hi = boot_ci_by_game([(b["g"], b["price"], b["won"]) for b in bets], 4000, 5)
P("")
P("  |gap| >= 1.0, bet toward Pinnacle:  n=%d  games=%d  W %d (%.1f%%)  ROI %+.1f%%  CI[%+.1f%%, %+.1f%%]"
  % (s["n"], s["g"], s["w"], 100*s["wr"], 100*s["roi"], 100*lo, 100*hi))
for lab, sel in (("over side", lambda b: b["side"] == "over"), ("under side", lambda b: b["side"] == "under")):
    t = summ([b for b in bets if sel(b)])
    P("     %-11s n=%-4d ROI %+.1f%%" % (lab, t["n"], 100*t["roi"]))
P("")
P("  (c) THRESHOLD PERTURBATION on the gap")
for g in (0.5, 1.0, 1.5, 2.0):
    bb = [b for b in bets if abs(b["gap"]) >= g] if g >= 1.0 else None
    if bb is None:
        bb = []
        for r in S:
            if abs(r["gap"]) < g: continue
            side = "over" if r["gap"] > 0 else "under"
            w = None if r["actual"] == r["line"] else ((r["actual"] > r["line"]) if side == "over" else (r["actual"] < r["line"]))
            bb.append(dict(g=r["gt"], price=(r["over"] if side == "over" else r["under"]), won=w, side=side, date=r["date"], gap=r["gap"], pl=r["pl"]))
    t = summ(bb)
    P("     |gap| >= %.1f  n=%-4d games=%-3d ROI %+7.1f%%  wr %.1f%%" % (g, t["n"], t["g"], 100*t["roi"], 100*t["wr"]))
P("")
P("  MECHANISM (Law 6): does the gap predict RAW PRODUCTION, i.e. does Pinnacle's line beat")
P("  1xbet's at forecasting the box score? statistic = (actual - 1xbet line) vs gap.")
z = [(r["actual"]-r["line"]) for r in S]
gp = [r["gap"] for r in S]
rho = spear(gp, z)
byp = collections.defaultdict(list)
for i, r in enumerate(S): byp[r["pl"]].append(i)
plists = [np.array(v) for v in byp.values()]
zz = np.array(z, float); T = 4000; beat = 0
for _ in range(T):
    y = zz.copy()
    for idx in plists: y[idx] = rng.permutation(y[idx])
    if spear(gp, y) >= rho: beat += 1
p_mech = (beat+1)/(T+1)
P("     rho(gap, actual - 1xbet line) = %+.4f  player-block perm p = %.4f   n=%d" % (rho, p_mech, len(S)))
sl = [r for r in S if abs(r["gap"]) >= 1]
mae_x = statistics.mean(abs(r["actual"]-r["line"]) for r in sl)
mae_p = statistics.mean(abs(r["actual"]-r["sharp"]) for r in sl)
P("     on |gap|>=1 rows: mean |actual - 1xbet line| = %.3f   mean |actual - Pinnacle line| = %.3f"
  % (mae_x, mae_p))
P("     -> Pinnacle is %s accurate than 1xbet on exactly the rows the rule bets" %
  ("MORE" if mae_p < mae_x else "LESS"))
# permutation on the ROI itself, permuting the gap sign/label within player
real = s["roi"]
rr = random.Random(51)
rows1 = [r for r in S if abs(r["gap"]) >= 1]
byp2 = collections.defaultdict(list)
for i, r in enumerate(rows1): byp2[r["pl"]].append(i)
sims = []
gaps = [r["gap"] for r in rows1]
for _ in range(4000):
    ng = list(gaps)
    for idx in byp2.values():
        v = [gaps[i] for i in idx]; rr.shuffle(v)
        for i, x in zip(idx, v): ng[i] = x
    tot = 0.0
    for r, g in zip(rows1, ng):
        side = "over" if g > 0 else "under"
        if r["actual"] == r["line"]: continue
        w = (r["actual"] > r["line"]) if side == "over" else (r["actual"] < r["line"])
        pr = r["over"] if side == "over" else r["under"]
        tot += (pr-1) if w else -1.0
    sims.append(tot/len(rows1))
sims.sort()
p_c2 = sum(1 for x in sims if x >= real)/len(sims)
P("     ROI permutation (gap reshuffled within player, direction follows the shuffled gap): p = %.4f" % p_c2)
PV["C2 sharp gap ROI"] = p_c2; PV["C2 sharp gap mechanism (rho)"] = p_mech
P("")
P("  (a) CHRONOLOGICAL WALK-FORWARD by game")
gs = sorted(set(b["g"] for b in bets)); sz = len(gs)/3
for i in range(3):
    sel = set(gs[int(i*sz):int((i+1)*sz)])
    t = summ([b for b in bets if b["g"] in sel])
    d = sorted(set(b["date"] for b in bets if b["g"] in sel))
    P("     fold %d  %s..%s  n=%-4d ROI %+7.1f%%  wr %.1f%%" % (i+1, d[0], d[-1], t["n"], 100*t["roi"], 100*t["wr"]))
P("     by month: " + "  ".join("%s n=%d ROI %+.1f%%" % (m, summ([b for b in bets if b["date"][:6] == m])["n"],
    100*summ([b for b in bets if b["date"][:6] == m])["roi"]) for m in sorted(set(b["date"][:6] for b in bets))))
P("     TIMING SENSITIVITY: the same rule with the sharp line read 12h out instead of 6h:")
S12 = [r for r in R if r["sharp12"] is not None]
b12 = []
for r in S12:
    g = round(r["sharp12"]-r["line"], 2)
    if abs(g) < 1: continue
    side = "over" if g > 0 else "under"
    w = None if r["actual"] == r["line"] else ((r["actual"] > r["line"]) if side == "over" else (r["actual"] < r["line"]))
    b12.append(dict(g=r["gt"], price=(r["over"] if side == "over" else r["under"]), won=w, date=r["date"]))
t = summ(b12)
P("       12h read: n=%-4d ROI %+.1f%%   (6h read: n=%d ROI %+.1f%%)" % (t["n"], 100*t["roi"], s["n"], 100*s["roi"]))
P("")
P("  (d) EXECUTION STRESS")
for c in (0.0, 0.01, 0.02, 0.03):
    t = summ([dict(b, price=b["price"]-c) for b in bets])
    P("     slip %.0fc  ROI %+7.1f%%" % (100*c, 100*t["roi"]))
P("     slippage to zero: %.1f cents" % (100*s["roi"]/max(s["wr"], 1e-9)))
rr2 = random.Random(77)
for m in (0.10, 0.25):
    acc = [summ([b for b in bets if rr2.random() > m])["roi"] for _ in range(2000)]
    P("     %d%% missed entries: mean ROI %+.1f%%  sd %.1f pp" % (100*m, 100*statistics.mean(acc), 100*statistics.pstdev(acc)))
P("     EXECUTION CAVEAT: the rule needs a Pinnacle prop line <=10h stale AND a two-sided 1xbet")
P("     quote at the same line, within a 6h window. That combination existed on %.1f%% of quotes." % (100*len(S)/len(R)))
seq = [0.0 if b["won"] is None else ((b["price"]-1) if b["won"] else -1.0) for b in bets]
P("  (e) BANKROLL flat 1u: final %+.2fu  max DD %.1fu  longest losing streak %d" % (
    sum(seq), drawdown(seq), longest_losing(seq)))

# ============================================================== C3
P("")
P("="*100)
P("C3  GAME-TOTAL GRADIENT  --  higher Pinnacle total -> better player overs")
P("="*100)
G = [r for r in R if r["tot"] is not None]
P("  n=%d quotes over %d games (gamelines.csv starts 2026-07-11, so June is absent)" % (
    len(G), len(set(r["gt"] for r in G))))
P("  MECHANISM (Law 6) on raw production, not ROI:")
z = [(r["actual"]-r["line"])/max(r["sd"] or 1, 1) for r in G]
tt = [r["tot"] for r in G]
rho = spear(tt, z)
# permute the game total across games -- the label lives on the game
gt_of = {}
for r in G: gt_of[r["gt"]] = r["tot"]
gids = sorted(gt_of); gidx = {g: i for i, g in enumerate(gids)}
garr = np.array([gidx[r["gt"]] for r in G]); gvals = np.array([gt_of[g] for g in gids])
zz = np.array(z, float); T = 4000; beat = 0
for _ in range(T):
    if spear(rng.permutation(gvals)[garr], zz) >= rho: beat += 1
p3m = (beat+1)/(T+1)
P("     rho(game total, standardised beat) = %+.4f   GAME-block label permutation p = %.4f" % (rho, p3m))
P("     does the total forecast the score at all? rho(total, realised total) = %+.4f  n=%d games" % (
    spear([gt_of[g] for g in gids], [next(r["realtot"] for r in G if r["gt"] == g) for g in gids]), len(gids)))
PV["C3 total gradient mechanism (rho)"] = p3m
P("")
P("  ROI by total tercile (over side, whole board):")
qs = np.quantile(gvals, [1/3., 2/3.])
def roi(v): return (sum((r["over"]-1) if r["actual"] > r["line"] else -1.0 for r in v)/len(v)) if v else 0.0
def wr(v): return 100*sum(1 for r in v if r["actual"] > r["line"])/len(v)
terc = []
for lab, sel in (("low  (<%.1f)" % qs[0], lambda r: r["tot"] < qs[0]),
                 ("mid", lambda r: qs[0] <= r["tot"] < qs[1]),
                 ("high (>=%.1f)" % qs[1], lambda r: r["tot"] >= qs[1])):
    v = [r for r in G if sel(r)]
    lo_, hi_ = boot_ci_by_game([(r["gt"], r["over"], r["actual"] > r["line"]) for r in v], 3000, 6)
    P("     %-15s n=%-5d games=%-3d over-rate %.1f%%  ROI %+6.1f%%  CI[%+.1f%%, %+.1f%%]" % (
        lab, len(v), len(set(r["gt"] for r in v)), wr(v), 100*roi(v), 100*lo_, 100*hi_))
    terc.append((lab, len(v), roi(v)))
P("     the best cell here is %+.1f%% against a DECLARED Grid-G noise ceiling of p95 = %+.1f%%" % (
    100*max(t[2] for t in terc), 100*json.load(open(os.path.join(D, "outputs", "t4_ceilings.json")))["gridG_p95"]))
P("")
P("  (c) BOUNDARY PERTURBATION (does the gradient survive moving the cut?)")
for q in (0.5, 0.6, 0.7, 0.75, 0.8):
    thr = float(np.quantile(gvals, q))
    v = [r for r in G if r["tot"] >= thr]
    P("     top %d%% of totals (>= %.1f)  n=%-5d ROI %+6.1f%%  over-rate %.1f%%" % (
        100*(1-q), thr, len(v), 100*roi(v), wr(v)))
P("")
P("  (a) WALK-FORWARD by game, top-tercile overs")
hv = [r for r in G if r["tot"] >= qs[1]]
gs = sorted(set(r["gt"] for r in hv)); sz = len(gs)/3
for i in range(3):
    sel = set(gs[int(i*sz):int((i+1)*sz)])
    v = [r for r in hv if r["gt"] in sel]
    P("     fold %d  n=%-4d ROI %+7.1f%%  over-rate %.1f%%" % (i+1, len(v), 100*roi(v), wr(v)))
P("")
P("  (d) EXECUTION: is the best total cell even above break-even?")
for c in (0.0, 0.01, 0.02, 0.03):
    P("     slip %.0fc  top-tercile over ROI %+.1f%%" % (
        100*c, 100*(sum((r["over"]-c-1) if r["actual"] > r["line"] else -1.0 for r in hv)/len(hv))))

# ============================================================== C4
P("")
P("="*100)
P("C4  VOLATILITY GRADIENT  --  high-variance players' overs underperform")
P("="*100)
V = [r for r in R if r["relvol"] is not None]
P("  n=%d quotes, %d games, %d player-market blocks" % (
    len(V), len(set(r["gt"] for r in V)), len(set((r["pl"], r["mk"]) for r in V))))
bl = {}
for r in V: bl.setdefault((r["pl"], r["mk"]), r["relvol"])
bk = sorted(bl); bidx = {k: i for i, k in enumerate(bk)}
barr = np.array([bidx[(r["pl"], r["mk"])] for r in V])
bv = np.array([bl[k] for k in bk])
z = np.array([(r["actual"]-r["line"])/max(r["sd"] or 1, 1) for r in V])
rho = spear(bv[barr], z)
bmk = [k[1] for k in bk]
mkg = collections.defaultdict(list)
for i, m in enumerate(bmk): mkg[m].append(i)
mkg = {k: np.array(v) for k, v in mkg.items()}
T = 4000; beat = 0
for _ in range(T):
    a = bv.copy()
    for m, idx in mkg.items(): a[idx] = rng.permutation(a[idx])
    if spear(a[barr], z) <= rho: beat += 1
p4m = (beat+1)/(T+1)
P("  MECHANISM (Law 6) on raw production: rho(relvol, standardised beat) = %+.4f" % rho)
P("     player-market label permutation WITHIN market, one-sided negative: p = %.4f" % p4m)
PV["C4 volatility gradient mechanism (rho)"] = p4m
P("")
P("  Over-side ROI by relvol tercile:")
q4 = np.quantile(bv, [1/3., 2/3.])
cells = []
for lab, sel in (("low vol", lambda r: bl[(r["pl"], r["mk"])] < q4[0]),
                 ("mid vol", lambda r: q4[0] <= bl[(r["pl"], r["mk"])] < q4[1]),
                 ("high vol", lambda r: bl[(r["pl"], r["mk"])] >= q4[1])):
    v = [r for r in V if sel(r)]
    lo_, hi_ = boot_ci_by_game([(r["gt"], r["over"], r["actual"] > r["line"]) for r in v], 3000, 7)
    u = sum((r["under"]-1) if r["actual"] < r["line"] else -1.0 for r in v)/len(v)
    P("     %-9s n=%-5d over-rate %.1f%%  overROI %+6.1f%% CI[%+.1f%%,%+.1f%%]   underROI %+6.1f%%" % (
        lab, len(v), wr(v), 100*roi(v), 100*lo_, 100*hi_, 100*u))
    cells.append((lab, roi(v), u, len(v)))
P("     NOTE the direction: high-vol OVERS do lose (%+.1f%%) but so does the whole board (-5.5%%)." % (100*cells[2][1],))
P("     The only tradable version is the UNDER on high-vol players: %+.1f%%, which is %s break-even." % (
    100*cells[2][2], "above" if cells[2][2] > 0 else "BELOW"))
P("")
P("  (c) BOUNDARY PERTURBATION")
for q in (0.5, 0.6, 2/3., 0.75, 0.8):
    thr = float(np.quantile(bv, q))
    v = [r for r in V if bl[(r["pl"], r["mk"])] >= thr]
    u = sum((r["under"]-1) if r["actual"] < r["line"] else -1.0 for r in v)/len(v)
    P("     top %2d%% relvol  n=%-5d overROI %+6.1f%%  underROI %+6.1f%%" % (
        round(100*(1-q)), len(v), 100*roi(v), 100*u))
P("")
P("  (a) WALK-FORWARD by game, top-tercile relvol")
hv4 = [r for r in V if bl[(r["pl"], r["mk"])] >= q4[1]]
gs = sorted(set(r["gt"] for r in hv4)); sz = len(gs)/3
for i in range(3):
    sel = set(gs[int(i*sz):int((i+1)*sz)])
    v = [r for r in hv4 if r["gt"] in sel]
    u = sum((r["under"]-1) if r["actual"] < r["line"] else -1.0 for r in v)/len(v)
    P("     fold %d  n=%-4d overROI %+7.1f%%  underROI %+7.1f%%" % (i+1, len(v), 100*roi(v), 100*u))
P("")
P("  CONFOUND: relvol = sd / line, so a low line mechanically inflates it.")
for lab, sel in (("line < 10", lambda r: r["line"] < 10), ("10-16", lambda r: 10 <= r["line"] < 16),
                 ("16-22", lambda r: 16 <= r["line"] < 22), ("22+", lambda r: r["line"] >= 22)):
    v = [r for r in V if sel(r)]
    hi_ = [r for r in v if bl[(r["pl"], r["mk"])] >= q4[1]]
    lo_ = [r for r in v if bl[(r["pl"], r["mk"])] < q4[0]]
    P("     %-9s  mean relvol %.3f | high-vol n=%-4d overROI %+6.1f%% | low-vol n=%-4d overROI %+6.1f%%" % (
        lab, statistics.mean(bl[(r["pl"], r["mk"])] for r in v), len(hi_), 100*roi(hi_) if hi_ else 0,
        len(lo_), 100*roi(lo_) if lo_ else 0))
P("     using RAW sd instead of sd/line (removes the line-size confound):")
bs = {}
for r in V: bs.setdefault((r["pl"], r["mk"]), r["sd"])
bsv = np.array([bs[k] for k in bk])
rho2 = spear(bsv[barr], z)
beat = 0
for _ in range(2000):
    a = bsv.copy()
    for m, idx in mkg.items(): a[idx] = rng.permutation(a[idx])
    if spear(a[barr], z) <= rho2: beat += 1
P("     rho(raw sd, standardised beat) = %+.4f   p = %.4f" % (rho2, (beat+1)/2001))
PV["C4 volatility gradient, raw sd"] = (beat+1)/2001

json.dump(PV, open(os.path.join(D, "outputs", "t4_c234_p.json"), "w"), indent=1)
open(os.path.join(D, "outputs", "t4_c234.txt"), "w", encoding="utf-8").write("\n".join(LOG))
