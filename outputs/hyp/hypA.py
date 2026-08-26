# hypA.py - NON-STAR PROPS ARE UNDERPRICED?
# Grid declared BEFORE looking: 4 usage-rank buckets x 8 market slices x 2 sides = 64 cells,
# min n = 60. Noise ceiling = p95 of the best cell under a PLAYER-BLOCK permutation of the
# rank label (rank is a player attribute -> permute at the player level).
import os, sys, json, random, statistics, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rolelib as L
random.seed(20260826)
HD = os.path.dirname(os.path.abspath(__file__))
ROWS = json.load(open(os.path.join(HD, "role_rows.json")))

MKS = ["pts", "reb", "ast", "pra", "pr", "pa", "ra"]
BUCK = [("1-2", lambda r: r["urank"] <= 2), ("3-4", lambda r: 3 <= r["urank"] <= 4),
        ("5-7", lambda r: 5 <= r["urank"] <= 7), ("8+",  lambda r: r["urank"] >= 8)]
MINN = 60
def bname(r):
    for nm, fn in BUCK:
        if fn(r): return nm
    return "?"
for r in ROWS: r["b"] = bname(r)

def cells(rows, key="b"):
    """returns {(bucket, market, side): [rows]} for the declared grid"""
    out = collections.defaultdict(list)
    for r in rows:
        out[(r[key], r["mk"], "over")].append(r); out[(r[key], r["mk"], "under")].append(r)
        out[(r[key], "ALL", "over")].append(r);   out[(r[key], "ALL", "under")].append(r)
    return out

def roi_of(rs, side):
    if not rs: return 0.0
    s = 0.0
    for r in rs:
        w = r["over_won"] if side == "over" else (not r["over_won"])
        s += (r["over_od" if side == "over" else "under_od"] - 1.0) if w else -1.0
    return 100.0*s/len(rs)

def blocks(rs, side):
    d = collections.defaultdict(list)
    for r in rs:
        w = r["over_won"] if side == "over" else (not r["over_won"])
        d[(r["tm"], r["tip"])].append((r["over_od" if side == "over" else "under_od"]-1.0) if w else -1.0)
    return list(d.values())

# ---------------- NOISE CEILING FIRST ----------------
# permute the rank BUCKET across players, preserving each player's own time-ordered sequence
bypg = collections.defaultdict(list)          # player -> ordered unique player-games
for r in ROWS: bypg[r["pl"]].append(r)
plist = sorted(bypg)
seq = {}
for p in plist:
    rs = sorted(bypg[p], key=lambda r: r["tip"])
    pgs = []
    for r in rs:
        if not pgs or pgs[-1][0] != r["tip"]: pgs.append((r["tip"], r["b"]))
    seq[p] = [b for _, b in pgs]

def permuted_labels(rng):
    order = plist[:]; rng.shuffle(order)
    lab = {}
    for p, q in zip(plist, order):
        s = seq[q] or ["3-4"]
        rs = sorted(bypg[p], key=lambda r: r["tip"])
        k = -1; last = None
        for r in rs:
            if r["tip"] != last: k += 1; last = r["tip"]
            lab[id(r)] = s[k % len(s)]
    return lab

def best_of_grid(labfn):
    C = collections.defaultdict(list)
    for r in ROWS:
        b = labfn(r)
        C[(b, r["mk"], "over")].append(r); C[(b, r["mk"], "under")].append(r)
        C[(b, "ALL", "over")].append(r);   C[(b, "ALL", "under")].append(r)
    best = -99.0
    for (b, mk, sd), rs in C.items():
        if len(rs) < MINN: continue
        v = roi_of(rs, sd)
        if v > best: best = v
    return best

T = 1200
rng = random.Random(11)
sims = []
for _ in range(T):
    lab = permuted_labels(rng)
    sims.append(best_of_grid(lambda r: lab[id(r)]))
sims.sort()
CEIL = sims[int(0.95*T)]
print("="*104)
print("HYPOTHESIS A - usage rank buckets. GRID DECLARED IN ADVANCE: 4 buckets x 8 market slices"
      " x 2 sides = 64 cells, n>=%d." % MINN)
print("PLAYER-BLOCK NULL (rank label shuffled between players, %d reps):" % T)
print("   best-cell-under-null: median %+.2f%%   p95 = %+.2f%%   max %+.2f%%" %
      (sims[T//2], CEIL, sims[-1]))
print("   >>> NOISE CEILING = %+.2f%% ROI. Nothing below this is a finding. <<<" % CEIL)
print("="*104)

# ---------------- base rates / artifact check ----------------
n = len(ROWS); ov = sum(1 for r in ROWS if r["over_won"])
print("\nBOARD BASE RATE (artifact guard): %d quotes, over hits %.2f%%  |  flat-over ROI %+.2f%%"
      "  flat-under ROI %+.2f%%" % (n, 100*ov/n, roi_of(ROWS, "over"), roi_of(ROWS, "under")))
print("  breakeven at the mean prop price: over %.2f%%  under %.2f%%" %
      (100*statistics.mean(1/r["over_od"] for r in ROWS),
       100*statistics.mean(1/r["under_od"] for r in ROWS)))

# ---------------- MECHANISM ON RAW PRODUCTION ----------------
print("\nMECHANISM (raw production, no prices): does the book set softer lines for low-usage"
      " players?  actual - line, and over-rate, by bucket")
print("  %-6s %6s %8s %9s %9s %8s" % ("bucket", "quotes", "players", "over%", "act-line", "med min"))
for nm, fn in BUCK:
    rs = [r for r in ROWS if r["b"] == nm]
    if not rs: continue
    print("  %-6s %6d %8d %8.2f%% %+9.3f %8.1f" %
          (nm, len(rs), len(set(r["pl"] for r in rs)),
           100*sum(1 for r in rs if r["over_won"])/len(rs),
           statistics.mean(r["actual"]-r["line"] for r in rs),
           statistics.median(r["medmin"] for r in rs)))

# ---------------- THE GRID ----------------
def table(rows, title, show_all=True):
    print("\n" + title)
    print("  %-6s %-4s %-6s %6s %7s %8s %9s %22s %s" %
          ("bucket", "mkt", "side", "n", "games", "hit%", "ROI", "block-boot 95% CI", "vs ceil"))
    C = cells(rows)
    got = []
    for (b, mk, sd), rs in C.items():
        if len(rs) < MINN: continue
        if not show_all and mk != "ALL": continue
        r_ = roi_of(rs, sd)
        got.append((r_, b, mk, sd, rs))
    got.sort(reverse=True)
    for r_, b, mk, sd, rs in got:
        bl = blocks(rs, sd)
        roi, lo, hi = L.block_boot(bl, 3000, random.Random(hash((b, mk, sd)) & 0xffff))
        hits = sum(1 for r in rs if (r["over_won"] if sd == "over" else not r["over_won"]))
        print("  %-6s %-4s %-6s %6d %7d %8.2f %+8.2f%% %22s %s" %
              (b, mk, sd, len(rs), len(bl), 100*hits/len(rs), roi,
               L.fmt_ci(lo, hi), "CLEARS" if roi >= CEIL else ""))
    return got

got = table(ROWS, "FULL GRID (all 64 declared cells with n>=%d), sorted by ROI:" % MINN)
print("\n  cells clearing the %+.2f%% ceiling: %d of %d" %
      (CEIL, sum(1 for x in got if x[0] >= CEIL), len(got)))

# ---------------- THE CENSORSHIP A/B ----------------
CEN = [r for r in ROWS if not r["newly"]]
print("\n" + "="*104)
print("DID THE NAME-JOIN FIX CHANGE THE ANSWER?  same cells on the OLD censored population"
      " (%d of %d rows, the 8 dropped players removed)" % (len(CEN), len(ROWS)))
print("="*104)
d = {}
for r_, b, mk, sd, rs in got: d[(b, mk, sd)] = r_
C2 = cells(CEN)
print("  %-6s %-4s %-6s %8s %8s %9s %9s" % ("bucket", "mkt", "side", "n_fix", "n_cens", "ROI_fix", "ROI_cens"))
rowsout = []
for (b, mk, sd), rs in sorted(C2.items()):
    if (b, mk, sd) not in d: continue
    if len(rs) < MINN: continue
    rowsout.append((abs(d[(b, mk, sd)] - roi_of(rs, sd)), b, mk, sd, len(rs), roi_of(rs, sd)))
rowsout.sort(reverse=True)
for delta, b, mk, sd, n2, r2 in rowsout[:14]:
    nf = sum(1 for r in ROWS if r["b"] == b and (mk == "ALL" or r["mk"] == mk))
    print("  %-6s %-4s %-6s %8d %8d %+8.2f%% %+8.2f%%   (moved %.2f pp)" %
          (b, mk, sd, nf, n2, d[(b, mk, sd)], r2, delta))
print("  median |ROI shift| across shared cells: %.2f pp   max %.2f pp" %
      (statistics.median([x[0] for x in rowsout]) if rowsout else 0,
       max([x[0] for x in rowsout]) if rowsout else 0))
# would the censored run have produced a different verdict?
b_fix = max(x[0] for x in got)
b_cen = max(roi_of(rs, sd) for (b, mk, sd), rs in C2.items() if len(rs) >= MINN)
print("  best cell FIXED %+.2f%%  vs  best cell CENSORED %+.2f%%   (ceiling %+.2f%%)" %
      (b_fix, b_cen, CEIL))
