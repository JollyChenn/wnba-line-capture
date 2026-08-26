# hypB2.py - the elevation IS real in minutes but the book has already priced it, and the
# elevated player UNDER-performs. Focused, tiny declared grid so the ceiling is tight; plus a
# control for the KNOWN line-raise effect, so this is not a rediscovery of gate-3 staleness.
import os, sys, json, random, statistics, collections, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rolelib as L
random.seed(20260826)
HD = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HD, "B_rows.json")))

g = L.boot(); prevline = g["prevline"]
def T(s): return datetime.datetime.fromisoformat(s)
for r in R:
    pv = prevline.get((r["pl"], r["mk"], T(r["tip"])))
    r["linemv"] = None if pv is None else r["line"] - pv

def rate(rs): return 100.0*sum(1 for r in rs if r["over_won"])/len(rs) if rs else 0.0
def roi_of(rs, side):
    s = 0.0
    for r in rs:
        w = r["over_won"] if side == "over" else (not r["over_won"])
        s += (r["over_od" if side == "over" else "under_od"]-1.0) if w else -1.0
    return 100.0*s/len(rs) if rs else 0.0
def blocks(rs, side):
    d = collections.defaultdict(list)
    for r in rs:
        w = r["over_won"] if side == "over" else (not r["over_won"])
        d[(r["tm"], r["tip"])].append((r["over_od" if side == "over" else "under_od"]-1.0) if w else -1.0)
    return list(d.values())

print("="*104)
print("DID THE BOOK MOVE HER LINE AFTER THE JUMP?  (if it did, any k=1 effect is the KNOWN")
print("  line-move/overshoot family, not a new role signal)")
print("="*104)
print("  %-22s %6s %10s %10s %8s" % ("group", "n", "mean linemv", "med linemv", "raised%"))
for lbl, sel in (("k_jump=1", lambda r: r["k_jump"] == 1),
                 ("k_jumpbig=1", lambda r: r["k_jumpbig"] == 1),
                 ("no jump", lambda r: r["k_jump"] is None)):
    rs = [r for r in R if sel(r) and r["linemv"] is not None]
    print("  %-22s %6d %+10.3f %+10.2f %7.1f%%" %
          (lbl, len(rs), statistics.mean(r["linemv"] for r in rs),
           statistics.median(r["linemv"] for r in rs),
           100*sum(1 for r in rs if r["linemv"] > 0)/len(rs)))

print("\n" + "="*104)
print("FOCUSED TEST. Declared grid = 2 cells: {JUMP k=1, JUMPBIG k=1} x {under}, ALL markets.")
print("NULL: per-player circular rotation of her jump timeline, 3000 reps.")
print("="*104)
bypl = collections.defaultdict(list)
for r in R: bypl[r["pl"]].append(r)
tl = {}
for p, rs in bypl.items():
    rs.sort(key=lambda r: r["tip"])
    gs = []
    for r in rs:
        if not gs or gs[-1] != r["tip"]: gs.append(r["tip"])
    tl[p] = (gs, {gg: i for i, gg in enumerate(gs)})
def rot(rng):
    lab = {}
    for p, rs in bypl.items():
        gs, idx = tl[p]; n = len(gs); off = rng.randrange(n)
        vec = {}
        for r in rs: vec.setdefault(idx[r["tip"]], (r["k_jump"], r["k_jumpbig"]))
        for r in rs: lab[id(r)] = vec.get((idx[r["tip"]]+off) % n, (None, None))
    return lab
def two(labfn):
    a = [r for r in R if labfn(r)[0] == 1]; b = [r for r in R if labfn(r)[1] == 1]
    return (roi_of(a, "under") if len(a) >= 40 else -99,
            roi_of(b, "under") if len(b) >= 40 else -99)
rng = random.Random(21); sims = []
for _ in range(3000):
    lab = rot(rng); sims.append(max(two(lambda r: lab[id(r)])))
sims.sort(); CEIL = sims[int(0.95*len(sims))]
print("  best-of-2 under null: median %+.2f%%  p95 = %+.2f%%   >>> CEILING %+.2f%% <<<" %
      (sims[len(sims)//2], CEIL, CEIL))
real = two(lambda r: (r["k_jump"], r["k_jumpbig"]))
for lbl, key, v in (("JUMP k=1 under", "k_jump", real[0]), ("JUMPBIG k=1 under", "k_jumpbig", real[1])):
    rs = [r for r in R if r[key] == 1]
    bl = blocks(rs, "under")
    roi, lo, hi = L.block_boot(bl, 4000, random.Random(2))
    hit = 100 - rate(rs)
    be = 100*statistics.mean(1/r["under_od"] for r in rs)
    print("  %-20s n=%d  games=%d  under hits %.2f%% (breakeven %.2f%%)  ROI %+.2f%%  CI %s  %s" %
          (lbl, len(rs), len(bl), hit, be, roi, L.fmt_ci(lo, hi), "CLEARS" if roi >= CEIL else ""))
beat = sum(1 for s in sims if s >= max(real))/len(sims)
print("  permutation p = %.4f" % beat)

print("\n" + "="*104)
print("RAW-PRODUCTION MECHANISM, isolated: over-rate the game AFTER a minutes jump, split by")
print("  whether the book raised her line. If the effect only lives in the RAISED half it is")
print("  the known overshoot family; if it lives in both it is a role signal.")
print("="*104)
print("  %-30s %6s %6s %8s %10s" % ("group", "n", "games", "over%", "z(act-line)"))
for lbl, sel in (("jump k=1, line RAISED", lambda r: r["k_jump"] == 1 and (r["linemv"] or 0) > 0),
                 ("jump k=1, line flat/cut", lambda r: r["k_jump"] == 1 and r["linemv"] is not None and r["linemv"] <= 0),
                 ("no jump, line RAISED", lambda r: r["k_jump"] is None and (r["linemv"] or 0) > 0),
                 ("no jump, line flat/cut", lambda r: r["k_jump"] is None and r["linemv"] is not None and r["linemv"] <= 0)):
    rs = [r for r in R if sel(r)]
    if len(rs) < 30: continue
    byk = collections.defaultdict(list)
    for r in R: byk[r["mk"]].append(r["actual"]-r["line"])
    mu = {k: statistics.mean(v) for k, v in byk.items()}
    sd = {k: statistics.pstdev(v) or 1 for k, v in byk.items()}
    print("  %-30s %6d %6d %7.2f%% %+10.3f" %
          (lbl, len(rs), len(set((r["tm"], r["tip"]) for r in rs)), rate(rs),
           statistics.mean(((r["actual"]-r["line"])-mu[r["mk"]])/sd[r["mk"]] for r in rs)))

print("\n" + "="*104)
print("MINUTES DOSE-RESPONSE, the part that IS real (no prices involved):")
print("="*104)
print("  %-14s %6s %14s %14s" % ("k after jump", "n pg", "mean min", "mean min-medmin"))
seenpg = {}
for r in R: seenpg[(r["pl"], r["tip"])] = r
for k in (1, 2, 3, 4, None):
    rs = [v for v in seenpg.values() if v["k_jump"] == k]
    if len(rs) < 20: continue
    print("  %-14s %6d %14.2f %+14.2f" % ("k=%s" % k, len(rs),
          statistics.mean(r["min"] for r in rs), statistics.mean(r["min"]-r["medmin"] for r in rs)))
