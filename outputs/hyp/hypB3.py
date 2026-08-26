# hypB3.py - the interaction that fell out of B: a minutes spike AND the book raising her line.
# This is the OPPOSITE sign to the brief's claim, and it was found post-hoc, so it gets a
# declared 12-cell grid and its own permutation ceiling before it is allowed to be a finding.
#   grid: k in {1,2,3} x {line RAISED, line flat/cut} x {over, under} = 12 cells, n>=60.
#   NULL: per-player circular rotation of the JUMP timeline (line-move stays where it is,
#   because the line-move family is already a known control - we are testing the jump).
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
R = [r for r in R if r["linemv"] is not None]
for r in R: r["rz"] = "RAISED" if r["linemv"] > 0 else "FLAT/CUT"
MINN = 60
def roi_of(rs, sd):
    if not rs: return -99
    s = 0.0
    for r in rs:
        w = r["over_won"] if sd == "over" else (not r["over_won"])
        s += (r["over_od" if sd == "over" else "under_od"]-1.0) if w else -1.0
    return 100.0*s/len(rs)
def blocks(rs, sd):
    d = collections.defaultdict(list)
    for r in rs:
        w = r["over_won"] if sd == "over" else (not r["over_won"])
        d[(r["tm"], r["tip"])].append((r["over_od" if sd == "over" else "under_od"]-1.0) if w else -1.0)
    return list(d.values())
def grid(labfn):
    o = {}
    for k in (1, 2, 3):
        for rz in ("RAISED", "FLAT/CUT"):
            rs = [r for r in R if labfn(r) == k and r["rz"] == rz]
            for sd in ("over", "under"):
                o[(k, rz, sd)] = roi_of(rs, sd) if len(rs) >= MINN else -99
    return o
bypl = collections.defaultdict(list)
for r in R: bypl[r["pl"]].append(r)
tl = {}
for p, rs in bypl.items():
    rs.sort(key=lambda r: r["tip"]); gs = []
    for r in rs:
        if not gs or gs[-1] != r["tip"]: gs.append(r["tip"])
    tl[p] = (gs, {x: i for i, x in enumerate(gs)})
def rot(rng):
    lab = {}
    for p, rs in bypl.items():
        gs, idx = tl[p]; n = len(gs); off = rng.randrange(n); vec = {}
        for r in rs: vec.setdefault(idx[r["tip"]], r["k_jump"])
        for r in rs: lab[id(r)] = vec.get((idx[r["tip"]]+off) % n)
    return lab
Tn = 3000; rng = random.Random(31); sims = []
for _ in range(Tn):
    lab = rot(rng); sims.append(max(grid(lambda r: lab[id(r)]).values()))
sims.sort(); CEIL = sims[int(0.95*Tn)]
print("="*104)
print("JUMP x LINE-MOVE INTERACTION. 12 declared cells, n>=%d, rows with a known previous line"
      " (%d of %d)." % (MINN, len(R), len(R)))
print("PER-PLAYER JUMP-ROTATION NULL, %d reps: best-of-12 median %+.2f%%  p95 = %+.2f%%  max %+.2f%%"
      % (Tn, sims[Tn//2], CEIL, sims[-1]))
print(">>> NOISE CEILING = %+.2f%% <<<" % CEIL)
print("="*104)
real = grid(lambda r: r["k_jump"])
print("  %-3s %-9s %-6s %6s %6s %8s %9s %22s %s" %
      ("k", "line", "side", "n", "games", "hit%", "ROI", "block-boot 95% CI", ""))
best = -99
for (k, rz, sd), v in sorted(real.items(), key=lambda kv: -kv[1]):
    if v == -99: continue
    rs = [r for r in R if r["k_jump"] == k and r["rz"] == rz]
    bl = blocks(rs, sd)
    roi, lo, hi = L.block_boot(bl, 5000, random.Random(4))
    hits = sum(1 for r in rs if (r["over_won"] if sd == "over" else not r["over_won"]))
    print("  %-3d %-9s %-6s %6d %6d %7.2f%% %+8.2f%% %22s %s" %
          (k, rz, sd, len(rs), len(bl), 100*hits/len(rs), roi, L.fmt_ci(lo, hi),
           "CLEARS" if roi >= CEIL else ""))
    best = max(best, v)
print("\n  best real cell %+.2f%%   ceiling %+.2f%%   permutation p = %.4f" %
      (best, CEIL, sum(1 for s in sims if s >= best)/Tn))

# per-market and independence detail on the headline cell
print("\nHEADLINE CELL DETAIL - k=1 & RAISED & under, per market (are 7 correlated markets doing"
      "\n  the work, or is it broad?)  and a player-game-level (one bet per player-game) version:")
rs = [r for r in R if r["k_jump"] == 1 and r["rz"] == "RAISED"]
for mk in ("pts", "reb", "ast", "pra", "pr", "pa", "ra"):
    s = [r for r in rs if r["mk"] == mk]
    if len(s) < 12: continue
    print("    %-4s n=%-4d under hits %5.1f%%  ROI %+7.2f%%" %
          (mk, len(s), 100*sum(1 for r in s if not r["over_won"])/len(s), roi_of(s, "under")))
one = {}
for r in sorted(rs, key=lambda r: (r["pl"], r["tip"], r["mk"])): one.setdefault((r["pl"], r["tip"]), r)
one = list(one.values())
roi, lo, hi = L.block_boot(blocks(one, "under"), 5000, random.Random(6))
print("    ONE BET PER PLAYER-GAME: n=%d  players=%d  games=%d  under hits %.1f%%  ROI %+.2f%%  CI %s" %
      (len(one), len(set(r["pl"] for r in one)), len(set((r["tm"], r["tip"]) for r in one)),
       100*sum(1 for r in one if not r["over_won"])/len(one), roi, L.fmt_ci(lo, hi)))
# walk-forward: does it hold in both halves of the season?
ds = sorted(set(r["date"] for r in R)); cut = ds[len(ds)//2]
for lbl, sel in (("first half  (<%s)" % cut, lambda r: r["date"] < cut),
                 ("second half (>=%s)" % cut, lambda r: r["date"] >= cut)):
    s = [r for r in rs if sel(r)]
    if not s: continue
    print("    %-22s n=%-4d games=%-3d under hits %5.1f%%  ROI %+7.2f%%" %
          (lbl, len(s), len(set((r["tm"], r["tip"]) for r in s)),
           100*sum(1 for r in s if not r["over_won"])/len(s), roi_of(s, "under")))
