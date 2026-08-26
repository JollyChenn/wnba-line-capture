# Benjamini-Hochberg across everything reconstructable, plus C2 bankroll, plus the report.
import platform; platform._wmi = None
import os, sys, json, random, statistics, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, D)
from t4_lib import base, bh, drawdown, longest_losing
LOG = []
def P(s=""):
    print(s); LOG.append(s)

# p-values logged in the repo's own write-ups (MODEL.md / CLV_HISTORY.md / handoffs)
REPO = [0.0000, 0.0095, 0.0095, 0.0207, 0.0207, 0.0207, 0.0302, 0.0302, 0.0560, 0.0560,
        0.0568, 0.077, 0.1288, 0.193, 0.213, 0.237, 0.324, 0.324, 0.3280, 0.4046,
        0.4105, 0.4505, 0.7432, 0.7432]
MINE = [
 ("C1  Model S ROI > 0 (game-clustered bootstrap, one-sided)",            0.0468),
 ("C1  starred-minus-raised contrast (player-block perm)",                0.0375),
 ("C1  staleness gradient on RAW PRODUCTION (player-block perm)",         0.0007),
 ("C1  staleness gradient on RAW PRODUCTION (game-block perm)",           0.0013),
 ("C1  signal night-specificity, ROI (within-player perm)",               0.4263),
 ("C1  signal night-specificity, RAW PRODUCTION (within-player perm)",    0.8705),
 ("C1  chronologically-clean player split (block label perm)",            0.2483),
 ("C2  sharp gap, live cell ROI (gap reshuffled within player)",          0.0158),
 ("C2  sharp gap ROI, |gap|>=1 (gap reshuffled within player)",           0.0173),
 ("C2  Pinnacle beats 1xbet at forecasting the box (player-block perm)",  0.0085),
 ("C3  total gradient on standardised beat (GAME-block label perm)",      0.3037),
 ("C3  total gradient on over_won (GAME-block label perm)",               0.4585),
 ("C3  total gradient on over PnL (GAME-block label perm)",               0.2143),
 ("C3  total gradient on raw production, unadjusted for the line",        0.0003),
 ("C4  relvol gradient (player-market label perm within market)",         0.0147),
 ("C4  same gradient using RAW sd, i.e. line-size confound removed",      0.5107),
]
P("="*100)
P("MULTIPLE TESTING  --  Benjamini-Hochberg at q = 0.10")
P("="*100)
P("  The corrected family is every p-value this project can be shown to have computed:")
P("  %d written down in MODEL.md / CLV_HISTORY.md / the handoffs, plus the %d computed in this" % (len(REPO), len(MINE)))
P("  audit = %d. THE TRUE NUMBER IS FAR LARGER. The repo holds 295 analysis scripts, most of" % (len(REPO)+len(MINE)))
P("  which sweep many cells and report only the winner; the brief's own DEAD list names 15")
P("  buried hypotheses that left no p-value behind. Treat what follows as a LOWER BOUND on")
P("  the correction: every unlogged test makes these thresholds stricter, never looser.")
P("")
allp = [("(repo, unnamed #%d)" % i, p) for i, p in enumerate(REPO, 1)] + MINE
res = bh(allp, q=0.10)
named = [r for r in res if not r[0].startswith("(repo")]
named.sort(key=lambda r: r[1])
P("  %-68s %8s %8s  %s" % ("test", "p", "BH crit", "survives q=0.10"))
for nm, p, crit, ok in named:
    P("  %-68s %8.4f %8.4f  %s" % (nm, p, crit, "YES" if ok else "no"))
nsurv = sum(1 for r in res if r[3])
P("")
P("  %d of %d tests in the corrected family survive BH at q=0.10." % (nsurv, len(res)))
P("  Of the four audited claims, the ones that survive are:")
for nm, p, crit, ok in named:
    if ok: P("     - " + nm)
P("")
P("  Bonferroni for reference (alpha 0.05 / %d = %.5f): " % (len(allp), 0.05/len(allp)))
for nm, p, crit, ok in named:
    if p <= 0.05/len(allp): P("     - %s  (p=%.4f)" % (nm, p))

# --------------------------------------------------------------- C2 bankroll
P("")
P("="*100)
P("C2 BANKROLL")
P("="*100)
R = base()
S = [r for r in R if r["sharp"] is not None]
bets = []
for r in S:
    g = r["sharp"]-r["line"]
    if abs(g) < 1: continue
    side = "over" if g > 0 else "under"
    w = None if r["actual"] == r["line"] else ((r["actual"] > r["line"]) if side == "over" else (r["actual"] < r["line"]))
    bets.append(dict(g=r["gt"], price=(r["over"] if side == "over" else r["under"]), won=w, date=r["date"]))
bets.sort(key=lambda b: b["date"])
seq = [0.0 if b["won"] is None else ((b["price"]-1) if b["won"] else -1.0) for b in bets]
gs = sorted(set(b["g"] for b in bets)); sz = len(gs)/3
oos = set(gs[int(sz):])
ob = [b for b in bets if b["g"] in oos]
wr_oos = sum(1 for b in ob if b["won"])/max(sum(1 for b in ob if b["won"] is not None), 1)
o = statistics.mean(b["price"] for b in bets); bb = o-1
fk = (wr_oos*bb - (1-wr_oos))/bb
P("  flat 1u over n=%d: final %+.2fu  max drawdown %.1fu  longest losing streak %d" % (
    len(bets), sum(seq), drawdown(seq), longest_losing(seq)))
P("  OOS (folds 2-3) win rate %.1f%% at mean odds %.3f -> full Kelly f = %.3f" % (100*wr_oos, o, fk))
for frac, nm in ((0.25, "1/4 Kelly"), (0.125, "1/8 Kelly")):
    f = max(0.0, fk*frac); eq = 100.0; peak = 100.0; mdd = 0.0
    for b in bets:
        st = eq*f
        if b["won"] is None: pass
        elif b["won"]: eq += st*(b["price"]-1)
        else: eq -= st
        peak = max(peak, eq); mdd = max(mdd, 100*(peak-eq)/peak)
    P("  %-10s stake %.1f%% of bank  final %.1fu from 100u  max DD %.1f%%" % (nm, 100*f, eq, mdd))
byg = collections.defaultdict(list)
for b in bets: byg[b["g"]].append(b)
keys = list(byg); rr = random.Random(5); dd50 = 0; bust = 0; T = 5000
for _ in range(T):
    eq = 100.0; peak = 100.0; worst = 0.0
    for _ in range(len(keys)):
        for b in byg[keys[rr.randrange(len(keys))]]:
            eq += 0.0 if b["won"] is None else ((b["price"]-1) if b["won"] else -1.0)
            peak = max(peak, eq); worst = max(worst, peak-eq)
    if worst >= 50: dd50 += 1
    if eq <= 0: bust += 1
P("  game-clustered resample on a 100u bank, flat 1u: P(50u drawdown) %.1f%%   P(ruin) %.1f%%" % (
    100*dd50/T, 100*bust/T))
P("  NOTE: at %d bets over %d games in nine weeks, the OOS win rate that feeds Kelly has a" % (len(bets), len(gs)))
P("  standard error of about %.1f pp. Sizing off it is sizing off noise; 1/8 Kelly here is" % (
    100*(wr_oos*(1-wr_oos)/max(len(ob), 1))**0.5))
P("  indistinguishable from flat staking in any way that matters.")
open(os.path.join(D, "outputs", "t4_final.txt"), "w", encoding="utf-8").write("\n".join(LOG))
