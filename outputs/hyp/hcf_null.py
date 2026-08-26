# NOISE CEILING for the claim's own estimator.
# The claim's estimator is corr(pts_G - med_G , pts_G1 - med_G) within-player demeaned.
# med_G is a TRAILING MEDIAN of the same series and appears on BOTH sides.
# Null: destroy ALL time ordering by permuting each player's own points within player
# (marginal distribution and n preserved, zero persistence by construction), then RE-COMPUTE
# the trailing median from the permuted series and re-run the identical estimator.
# If the null reproduces a big positive number, the +0.191 is a shared-baseline artifact.
import os, sys, math, random, statistics, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hlib; ROOT = hlib.boot(globals())
random.seed(20260826)

def slope_corr(x, y):
    n = len(x); mx = sum(x)/n; my = sum(y)/n
    sxy = sum((a-mx)*(b-my) for a, b in zip(x, y))
    sxx = sum((a-mx)**2 for a in x); syy = sum((b-my)**2 for b in y)
    if sxx <= 0 or syy <= 0: return 0.0, 0.0
    return sxy/sxx, sxy/math.sqrt(sxx*syy)

# player sequences, same filters the panel uses
seq = {}
for pl, v in hist.items():
    s = sorted([x for x in v if x["min"] >= 8 and x["tm"] == teamof.get(pl)], key=lambda x: x["tip"])
    if len(s) >= 8: seq[pl] = [x["pts"] for x in s]
print("sim panel: %d players, %d player-games" % (len(seq), sum(len(v) for v in seq.values())))

def estimator(series_by_player, mode):
    """mode 'shared' = claim's version (same med_G both sides); 'own' = each game its own
       pre-game median; 'raw' = no baseline."""
    pairs = collections.defaultdict(list)
    for pl, s in series_by_player.items():
        for i in range(len(s)-1):
            prior = s[max(0, i-10):i]
            if len(prior) < 5: continue
            mg = statistics.median(prior)
            prior_n = s[max(0, i+1-10):i+1]
            mn = statistics.median(prior_n) if len(prior_n) >= 5 else None
            if mode == "shared": pairs[pl].append((s[i]-mg, s[i+1]-mg))
            elif mode == "own":
                if mn is None: continue
                pairs[pl].append((s[i]-mg, s[i+1]-mn))
            else: pairs[pl].append((s[i], s[i+1]))
    xs, ys = [], []
    for pl, v in pairs.items():
        if len(v) < 5: continue
        mx = sum(a for a, b in v)/len(v); my = sum(b for a, b in v)/len(v)
        for a, b in v: xs.append(a-mx); ys.append(b-my)
    return slope_corr(xs, ys), len(xs)

print("")
print("%-8s %10s %10s   %s" % ("mode", "obs corr", "n", "meaning"))
obs = {}
for mode, why in [("shared", "the claim's estimator (med_G on both sides)"),
                  ("own", "each game its own pre-game median"),
                  ("raw", "no baseline, player fixed effect only")]:
    (b, r), n = estimator(seq, mode)
    obs[mode] = r
    print("%-8s %+10.4f %10d   %s" % (mode, r, n, why))

print("")
print("NULL (points permuted within player -> ZERO true persistence, median recomputed):")
B = 400
null = {"shared": [], "own": [], "raw": []}
for _ in range(B):
    sim = {}
    for pl, s in seq.items():
        v = list(s); random.shuffle(v); sim[pl] = v
    for mode in null:
        null[mode].append(estimator(sim, mode)[0][1])
print("%-8s %10s %10s %10s %10s %10s" % ("mode", "null mean", "null p5", "null p95", "observed", "obs-mean"))
for mode in ("shared", "own", "raw"):
    v = sorted(null[mode])
    print("%-8s %+10.4f %+10.4f %+10.4f %+10.4f %+10.4f" % (
        mode, statistics.mean(v), v[int(.05*B)], v[int(.95*B)], obs[mode], obs[mode]-statistics.mean(v)))
print("")
print("A permutation that shuffles only the LABEL/y while keeping the observed med_G fixed")
print("cannot see this bias: med_G's within-player variance is carried into the covariance")
print("identically in every such permutation, so it cancels out of the reference distribution.")
