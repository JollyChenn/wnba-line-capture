# hypA2.py - the SHARP form of hypothesis A, on a tiny declared grid so the ceiling is tight.
#   grid: {top-4, outside-top-4} x {over, under} = 4 cells, n>=500 each. plus a monotone
#   trend test of over-rate against usage rank, player-block permuted.
import os, sys, json, random, statistics, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rolelib as L
random.seed(20260826)
HD = os.path.dirname(os.path.abspath(__file__))
ROWS = json.load(open(os.path.join(HD, "role_rows.json")))
for r in ROWS: r["nonstar"] = r["urank"] >= 5

def roi_of(rs, side):
    s = 0.0
    for r in rs:
        w = r["over_won"] if side == "over" else (not r["over_won"])
        s += (r["over_od" if side == "over" else "under_od"]-1.0) if w else -1.0
    return 100.0*s/len(rs)
def blocks(rs, side):
    d = collections.defaultdict(list)
    for r in rs:
        w = r["over_won"] if side == "over" else (not r["over_won"])
        d[(r["tm"], r["tip"])].append((r["over_od" if side == "over" else "under_od"]-1.0) if w else -1.0)
    return list(d.values())

bypl = collections.defaultdict(list)
for r in ROWS: bypl[r["pl"]].append(r)
plist = sorted(bypl)
seqs = {}
for p in plist:
    rs = sorted(bypl[p], key=lambda r: r["tip"]); pg = []
    for r in rs:
        if not pg or pg[-1][0] != r["tip"]: pg.append((r["tip"], r["urank"]))
    seqs[p] = [u for _, u in pg]
def perm(rng):
    order = plist[:]; rng.shuffle(order); lab = {}
    for p, q in zip(plist, order):
        s = seqs[q] or [3]
        rs = sorted(bypl[p], key=lambda r: r["tip"]); k = -1; last = None
        for r in rs:
            if r["tip"] != last: k += 1; last = r["tip"]
            lab[id(r)] = s[k % len(s)]
    return lab

def grid4(labfn):
    out = {}
    for side in ("over", "under"):
        for ns in (True, False):
            rs = [r for r in ROWS if (labfn(r) >= 5) == ns]
            out[(ns, side)] = roi_of(rs, side) if len(rs) >= 500 else -99
    return out

T = 2000; rng = random.Random(3); sims = []
for _ in range(T):
    lab = perm(rng)
    sims.append(max(grid4(lambda r: lab[id(r)]).values()))
sims.sort(); CEIL = sims[int(0.95*T)]
print("="*100)
print("HYPOTHESIS A (sharp form): {top-4 usage, outside top-4} x {over, under} = 4 cells, n>=500.")
print("PLAYER-BLOCK NULL, %d reps: best-of-4 median %+.2f%%  p95 = %+.2f%%" % (T, sims[T//2], CEIL))
print(">>> NOISE CEILING = %+.2f%% <<<" % CEIL)
print("="*100)
real = grid4(lambda r: r["urank"])
print("  %-16s %-6s %7s %7s %8s %8s %22s" % ("group", "side", "n", "games", "hit%", "ROI", "block-boot CI"))
for (ns, side), v in sorted(real.items(), key=lambda kv: -kv[1]):
    rs = [r for r in ROWS if r["nonstar"] == ns]
    bl = blocks(rs, side)
    roi, lo, hi = L.block_boot(bl, 4000, random.Random(5))
    hits = sum(1 for r in rs if (r["over_won"] if side == "over" else not r["over_won"]))
    print("  %-16s %-6s %7d %7d %7.2f%% %+7.2f%% %22s %s" %
          ("outside top-4" if ns else "top-4", side, len(rs), len(bl), 100*hits/len(rs), roi,
           L.fmt_ci(lo, hi), "CLEARS" if roi >= CEIL else ""))
beat = sum(1 for s in sims if s >= max(real.values()))
print("  best real cell %+.2f%%   permutation p = %.4f" % (max(real.values()), beat/T))

# ---- MONOTONE TREND on RAW PRODUCTION (mechanism, no prices) ----
print("\nMECHANISM TREND: correlation of usage rank with (actual - line), player-game level,")
print("  z-scored within market so the seven markets are comparable.")
byk = collections.defaultdict(list)
for r in ROWS: byk[r["mk"]].append(r["actual"]-r["line"])
mu = {k: statistics.mean(v) for k, v in byk.items()}
sd = {k: statistics.pstdev(v) or 1 for k, v in byk.items()}
for r in ROWS: r["z"] = ((r["actual"]-r["line"]) - mu[r["mk"]])/sd[r["mk"]]
def slope(labfn):
    xs = [labfn(r) for r in ROWS]; ys = [r["z"] for r in ROWS]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((a-mx)*(b-my) for a, b in zip(xs, ys)); den = sum((a-mx)**2 for a in xs)
    return num/den if den else 0.0
s_real = slope(lambda r: min(r["urank"], 10))
rng2 = random.Random(9); ss = []
for _ in range(2000):
    lab = perm(rng2); ss.append(slope(lambda r: min(lab[id(r)], 10)))
ss.sort()
p2 = 2*min(sum(1 for x in ss if x >= s_real), sum(1 for x in ss if x <= s_real))/len(ss)
print("  slope of z(actual-line) per rank step = %+.4f sd   (null 95%% band %+.4f .. %+.4f)  p=%.4f" %
      (s_real, ss[int(0.025*len(ss))], ss[int(0.975*len(ss))], p2))
print("  claim predicts a POSITIVE slope (worse-ranked -> more over). observed sign: %s" %
      ("POSITIVE (as claimed)" if s_real > 0 else "NEGATIVE - claim falsified in direction"))

# ---- per-rank raw table ----
print("\n  rank  quotes  players   over%%   mean(act-line)  med line  med min")
for k in range(1, 11):
    rs = [r for r in ROWS if (r["urank"] == k if k < 10 else r["urank"] >= 10)]
    if len(rs) < 25: continue
    print("  %-5s %6d %8d %7.2f%% %13.3f %9.1f %8.1f" %
          (str(k) if k < 10 else "10+", len(rs), len(set(r["pl"] for r in rs)),
           100*sum(1 for r in rs if r["over_won"])/len(rs),
           statistics.mean(r["actual"]-r["line"] for r in rs),
           statistics.median(r["line"] for r in rs), statistics.median(r["medmin"] for r in rs)))
