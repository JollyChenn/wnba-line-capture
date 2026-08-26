# Is the Model S edge a PLAYER effect rather than a NIGHT effect? And does the player version
# survive when the player set is built strictly from the past (no look-ahead)?
import platform; platform._wmi = None
import os, sys, json, random, statistics, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, D)
from t4_lib import base, boot_ci_by_game
R = base()
SIGS = ("flip", "hotover", "overshoot"); BM = ("pra", "pr", "pts")
LOG = []
def P(s=""):
    print(s); LOG.append(s)
A = sorted([r for r in R if r["prev"] is not None and r["mk"] in BM], key=lambda r: r["gt"])
for r in A: r["mv"] = r["line"]-r["prev"]
gp = [r for r in A if r["mv"] <= 0]
def roi(v): return (sum((r["over"]-1) if r["actual"] > r["line"] else -1.0 for r in v)/len(v)) if v else 0.0
def bci(v, s=2): return boot_ci_by_game([(r["gt"], r["over"], r["actual"] > r["line"]) for r in v], 3000, s)

P("="*100)
P("C1c  IS IT A PLAYER EFFECT?  chronologically clean 'signal has fired on her before'")
P("="*100)
fired = set()
prior_hit, prior_miss = [], []
for r in sorted(A, key=lambda x: x["gt"]):
    key = (r["pl"], r["mk"])
    if r["mv"] <= 0:
        (prior_hit if key in fired else prior_miss).append(r)
    if any(s in SIGS for s in r["srcs"]): fired.add(key)
lo, hi = bci(prior_hit)
P("  gate-PASS rows, signal HAS fired on this player-market in an EARLIER game:")
P("     n=%-5d games=%-4d ROI %+.1f%%  CI[%+.1f%%, %+.1f%%]  over-rate %.1f%%" % (
    len(prior_hit), len(set(r["gt"] for r in prior_hit)), 100*roi(prior_hit), 100*lo, 100*hi,
    100*sum(1 for r in prior_hit if r["actual"] > r["line"])/len(prior_hit)))
lo2, hi2 = bci(prior_miss, 3)
P("  gate-PASS rows, it never has:")
P("     n=%-5d games=%-4d ROI %+.1f%%  CI[%+.1f%%, %+.1f%%]  over-rate %.1f%%" % (
    len(prior_miss), len(set(r["gt"] for r in prior_miss)), 100*roi(prior_miss), 100*lo2, 100*hi2,
    100*sum(1 for r in prior_miss if r["actual"] > r["line"])/len(prior_miss)))
tonight = [r for r in prior_hit if any(s in SIGS for s in r["srcs"])]
other = [r for r in prior_hit if not any(s in SIGS for s in r["srcs"])]
P("  inside the 'has fired before' set:  signal TONIGHT n=%-4d ROI %+.1f%%   |  quiet night n=%-4d ROI %+.1f%%"
  % (len(tonight), 100*roi(tonight), len(other), 100*roi(other)))
P("  -> the night-specific increment is %+.1f pp; the between-player split is %+.1f pp"
  % (100*(roi(tonight)-roi(other)), 100*(roi(prior_hit)-roi(prior_miss))))
P("")
P("  CONFOUND CHECK: 'signal has fired before' is heavily correlated with volume and role.")
P("     mean prior games   fired-before %.1f  vs never %.1f" % (
    statistics.mean(r["nprior"] for r in prior_hit), statistics.mean(r["nprior"] for r in prior_miss)))
P("     mean line          fired-before %.1f  vs never %.1f" % (
    statistics.mean(r["line"] for r in prior_hit), statistics.mean(r["line"] for r in prior_miss)))
P("     mean minutes       fired-before %.1f  vs never %.1f" % (
    statistics.mean(r["minutes"] for r in prior_hit), statistics.mean(r["minutes"] for r in prior_miss)))
P("     mean (recent mean - line)  fired-before %+.2f  vs never %+.2f" % (
    statistics.mean(r["mean_ct"]-r["line"] for r in prior_hit if r["mean_ct"]),
    statistics.mean(r["mean_ct"]-r["line"] for r in prior_miss if r["mean_ct"])))
P("")
P("  Does the split survive matching on line size? (line is the crudest proxy for role)")
for lo_, hi_ in ((0, 9.99), (10, 15.99), (16, 21.99), (22, 99)):
    a = [r for r in prior_hit if lo_ <= r["line"] <= hi_]
    b = [r for r in prior_miss if lo_ <= r["line"] <= hi_]
    if len(a) < 40 or len(b) < 40:
        P("     line %2d-%-5.1f  fired n=%-4d ROI %+6.1f%% | never n=%-4d ROI %+6.1f%%   (thin)" % (
            lo_, hi_, len(a), 100*roi(a), len(b), 100*roi(b)))
        continue
    P("     line %2d-%-5.1f  fired n=%-4d ROI %+6.1f%% | never n=%-4d ROI %+6.1f%%" % (
        lo_, hi_, len(a), 100*roi(a), len(b), 100*roi(b)))
P("")
P("  WALK-FORWARD on the player split (3 chronological game folds):")
gs = sorted(set(r["gt"] for r in gp)); k = 3; sz = len(gs)/k
for i in range(k):
    sel = set(gs[int(i*sz):int((i+1)*sz)])
    a = [r for r in prior_hit if r["gt"] in sel]; b = [r for r in prior_miss if r["gt"] in sel]
    P("     fold %d  fired n=%-4d ROI %+6.1f%%  |  never n=%-4d ROI %+6.1f%%" % (
        i+1, len(a), 100*roi(a), len(b), 100*roi(b)))
P("")
P("  PERMUTATION at the label's level: 'has fired before' is a player-market attribute that")
P("  turns on at a point in time. Null = reassign the whole fired/never label across")
P("  player-market blocks within the same market, preserving how many blocks carry it.")
byb = collections.defaultdict(list)
for r in gp: byb[(r["pl"], r["mk"])].append(r)
lab = {}
for k2, v in byb.items(): lab[k2] = any(r in prior_hit for r in v)
# label at block level = did this block ever have a prior-fire row
blocks = list(byb)
mkof = {b: b[1] for b in blocks}
real = roi(prior_hit) - roi(prior_miss)
rr = random.Random(31)
bymk = collections.defaultdict(list)
for b in blocks: bymk[mkof[b]].append(b)
sims = []
for _ in range(3000):
    m = {}
    for mk, bs in bymk.items():
        vals = [lab[b] for b in bs]; rr.shuffle(vals)
        for b, v in zip(bs, vals): m[b] = v
    a = [r for b in blocks if m[b] for r in byb[b]]
    b_ = [r for b in blocks if not m[b] for r in byb[b]]
    if a and b_: sims.append(roi(a)-roi(b_))
sims.sort()
pv = sum(1 for x in sims if x >= real)/len(sims)
P("     real %+.1f pp | null mean %+.1f pp sd %.1f pp p95 %+.1f pp -> p = %.4f" % (
    100*real, 100*statistics.mean(sims), 100*statistics.pstdev(sims), 100*sims[int(.95*len(sims))], pv))
json.dump({"p_playersplit": pv, "roi_hit": roi(prior_hit), "roi_miss": roi(prior_miss),
           "n_hit": len(prior_hit), "n_miss": len(prior_miss)},
          open(os.path.join(D, "outputs", "t4_c1c.json"), "w"))
open(os.path.join(D, "outputs", "t4_c1c.txt"), "w", encoding="utf-8").write("\n".join(LOG))
