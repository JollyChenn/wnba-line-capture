# Is the surviving lag-1 persistence in POINTS anything other than minutes/role?
# Null: permute each player's (pts,min) GAME TUPLES within player -> ordering destroyed,
# the within-game pts~min link preserved. Correct centring for the demeaning (Nickell) bias.
import os, sys, math, random, statistics, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hlib; ROOT = hlib.boot(globals())
random.seed(20260826)

def corr(x, y):
    n = len(x); mx = sum(x)/n; my = sum(y)/n
    sxy = sum((a-mx)*(b-my) for a, b in zip(x, y))
    sxx = sum((a-mx)**2 for a in x); syy = sum((b-my)**2 for b in y)
    return sxy/math.sqrt(sxx*syy) if sxx > 0 and syy > 0 else 0.0

seq = {}
for pl, v in hist.items():
    s = sorted([x for x in v if x["min"] >= 8 and x["tm"] == teamof.get(pl)], key=lambda x: x["tip"])
    if len(s) >= 8: seq[pl] = [(x["pts"], x["min"]) for x in s]
print("panel: %d players, %d player-games" % (len(seq), sum(len(v) for v in seq.values())))

def stats(S):
    # pooled within-player pts~min slope, then three lag-1 correlations
    dx, dy = [], []
    for pl, s in S.items():
        mp = sum(a for a, b in s)/len(s); mm = sum(b for a, b in s)/len(s)
        for a, b in s: dx.append(b-mm); dy.append(a-mp)
    n = len(dx); mx = sum(dx)/n; my = sum(dy)/n
    sl = sum((a-mx)*(b-my) for a, b in zip(dx, dy)) / sum((a-mx)**2 for a in dx)
    out = {}
    for key, fn in [("pts", lambda a, b: a),
                    ("min", lambda a, b: b),
                    ("p/m", lambda a, b: a/b if b else None),
                    ("pts|min", lambda a, b: a - sl*b)]:
        X, Y = [], []
        for pl, s in S.items():
            v = [(fn(a, b), fn(c, d)) for (a, b), (c, d) in zip(s[:-1], s[1:])]
            v = [t for t in v if t[0] is not None and t[1] is not None]
            if len(v) < 5: continue
            ma = sum(t[0] for t in v)/len(v); mb = sum(t[1] for t in v)/len(v)
            for t in v: X.append(t[0]-ma); Y.append(t[1]-mb)
        out[key] = (corr(X, Y), len(X))
    return out

obs = stats(seq)
B = 400
null = collections.defaultdict(list)
for _ in range(B):
    sim = {}
    for pl, s in seq.items():
        v = list(s); random.shuffle(v); sim[pl] = v
    st = stats(sim)
    for k, (r, n) in st.items(): null[k].append(r)

print("")
print("%-9s %8s %10s %10s %10s %10s %8s" % ("series", "n", "observed", "null mean", "null p5", "null p95", "excess"))
for k in ("pts", "min", "p/m", "pts|min"):
    v = sorted(null[k]); r, n = obs[k]
    cnt = sum(1 for z in v if abs(z - statistics.mean(v)) >= abs(r - statistics.mean(v)))
    print("%-9s %8d %+10.4f %+10.4f %+10.4f %+10.4f %+8.4f  p=%.3f" % (
        k, n, r, statistics.mean(v), v[int(.05*B)], v[int(.95*B)], r-statistics.mean(v), (cnt+1)/(B+1)))
print("")
print("Read: 'min' carries the persistence. 'p/m' and 'pts|min' are the scoring-RATE tests -")
print("if they sit inside the null band, nothing about SCORING persists once volume is held.")
