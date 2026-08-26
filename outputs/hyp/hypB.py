# hypB.py - BACKUP ELEVATED BY INJURY. Mechanism on raw production first, then priced ROI.
# GRID DECLARED IN ADVANCE: 3 event arms (JUMP / JUMPBIG=genuine backup / GONE=heavy mate
# missing) x game-index 1,2,3 after the event x 2 sides x 2 market slices (ALL, pts) = 36
# cells, plus the pre-tip OUTNOW arm x 2 sides x 2 slices = 4 -> 40 cells, n>=40.
# NULL: per-player CIRCULAR ROTATION of her event-label timeline across her own team-games
# (the claim is about WHEN in her season the elevation lands, so that is what we scramble).
import os, sys, json, random, statistics, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rolelib as L
random.seed(20260826)
HD = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HD, "B_rows.json")))
MINN = 40

def roi_of(rs, side):
    if not rs: return -99
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
def zline(rows):
    byk = collections.defaultdict(list)
    for r in rows: byk[r["mk"]].append(r["actual"]-r["line"])
    mu = {k: statistics.mean(v) for k, v in byk.items()}
    sd = {k: statistics.pstdev(v) or 1 for k, v in byk.items()}
    for r in rows: r["z"] = ((r["actual"]-r["line"]) - mu[r["mk"]])/sd[r["mk"]]
zline(R)

print("="*106)
print("MECHANISM 1 (RAW PRODUCTION, NO PRICES). Tonight a team-mate with >=25 median minutes is")
print("  absent from the box or flagged out. Do the remaining players beat their posted lines?")
print("="*106)
print("  %-34s %6s %6s %8s %10s %10s %10s" %
      ("group", "n", "games", "over%", "act-line", "z", "min-medmin"))
def show(lbl, rs):
    if not rs: return
    print("  %-34s %6d %6d %7.2f%% %+10.3f %+10.3f %+10.2f" %
          (lbl, len(rs), len(set((r["tm"], r["tip"]) for r in rs)),
           100*sum(1 for r in rs if r["over_won"])/len(rs),
           statistics.mean(r["actual"]-r["line"] for r in rs),
           statistics.mean(r["z"] for r in rs),
           statistics.mean(r["min"]-r["medmin"] for r in rs)))
show("no heavy mate missing", [r for r in R if r["n_abs"] == 0])
show("1 heavy mate missing", [r for r in R if r["n_abs"] == 1])
show("2+ heavy mates missing", [r for r in R if r["n_abs"] >= 2])
show("  ...of those, BACKUPS (med<=22m)", [r for r in R if r["n_abs"] >= 1 and r["backup"]])
show("  ...of those, STARTERS (>22m)", [r for r in R if r["n_abs"] >= 1 and not r["backup"]])
show("PRE-TIP flag only: mate Out/Doubtful", [r for r in R if r["n_out_now"] >= 1])
show("  ...BACKUPS with mate flagged out", [r for r in R if r["n_out_now"] >= 1 and r["backup"]])

print("\n" + "="*106)
print("MECHANISM 2 (DOSE-RESPONSE, RAW). k = how many of her team's games ago the minutes jump")
print("  happened. The claim needs a decaying positive at k=1,2,3 and nothing at k=None.")
print("="*106)
for arm, key in (("JUMP (any player, +7min over trailing median)", "k_jump"),
                 ("JUMPBIG (base <=22m, jumped to >=26m)", "k_jumpbig"),
                 ("GONE (heavy mate missing that game)", "k_gone")):
    print("\n  " + arm)
    print("  %-14s %6s %6s %8s %10s %10s %10s" %
          ("k", "n", "games", "over%", "act-line", "z", "min-medmin"))
    for k in (1, 2, 3, 4, None):
        rs = [r for r in R if r[key] == k]
        if len(rs) < 20: continue
        show("k=%s" % k, rs)

# ---------------- ROI GRID + CEILING ----------------
ARMS = [("JUMP", "k_jump"), ("JUMPBIG", "k_jumpbig"), ("GONE", "k_gone")]
SL = [("ALL", lambda r: True), ("pts", lambda r: r["mk"] == "pts")]
def grid(labfn):
    out = {}
    for aname, key in ARMS:
        for k in (1, 2, 3):
            for sn, sf in SL:
                base = [r for r in R if sf(r) and labfn(r, key) == k]
                for sd in ("over", "under"):
                    out[(aname, k, sn, sd)] = roi_of(base, sd) if len(base) >= MINN else -99
    for sn, sf in SL:
        base = [r for r in R if sf(r) and r["n_out_now"] >= 1]
        for sd in ("over", "under"):
            out[("OUTNOW", 0, sn, sd)] = roi_of(base, sd) if len(base) >= MINN else -99
    return out

# per-player circular rotation of the event timeline
bypl = collections.defaultdict(list)
for r in R: bypl[r["pl"]].append(r)
tl = {}
for p, rs in bypl.items():
    rs.sort(key=lambda r: r["tip"])
    gs = []
    for r in rs:
        if not gs or gs[-1] != r["tip"]: gs.append(r["tip"])
    tl[p] = (gs, {g: i for i, g in enumerate(gs)})
def rotated(rng):
    lab = {}
    for p, rs in bypl.items():
        gs, idx = tl[p]; n = len(gs)
        off = rng.randrange(n)
        vec = {}
        for r in rs:
            vec.setdefault(idx[r["tip"]], {k: r[k] for _, k in ARMS})
        for r in rs:
            src = vec.get((idx[r["tip"]] + off) % n, {k: None for _, k in ARMS})
            lab[(id(r))] = src
    return lab

Tn = 800; rng = random.Random(17); sims = []
for _ in range(Tn):
    lab = rotated(rng)
    sims.append(max(grid(lambda r, key: lab[id(r)][key]).values()))
sims.sort(); CEIL = sims[int(0.95*Tn)]
print("\n" + "="*106)
print("PRICED ROI. GRID = 40 declared cells, n>=%d." % MINN)
print("PER-PLAYER CIRCULAR-ROTATION NULL, %d reps: best-of-grid median %+.2f%%  p95 = %+.2f%%  max %+.2f%%"
      % (Tn, sims[Tn//2], CEIL, sims[-1]))
print(">>> NOISE CEILING = %+.2f%% ROI. Under it is not a finding. <<<" % CEIL)
print("="*106)
real = grid(lambda r, key: r[key])
print("  %-9s %-3s %-4s %-6s %6s %6s %8s %9s %22s %s" %
      ("arm", "k", "mkt", "side", "n", "games", "hit%", "ROI", "block-boot 95% CI", ""))
seen = []
for (a, k, sn, sd), v in sorted(real.items(), key=lambda kv: -kv[1]):
    if v == -99: continue
    if a == "OUTNOW": rs = [r for r in R if (sn == "ALL" or r["mk"] == "pts") and r["n_out_now"] >= 1]
    else:
        key = dict(ARMS)[a]
        rs = [r for r in R if (sn == "ALL" or r["mk"] == "pts") and r[key] == k]
    bl = blocks(rs, sd)
    roi, lo, hi = L.block_boot(bl, 3000, random.Random(hash((a, k, sn, sd)) & 0xffff))
    hits = sum(1 for r in rs if (r["over_won"] if sd == "over" else not r["over_won"]))
    print("  %-9s %-3s %-4s %-6s %6d %6d %7.2f%% %+8.2f%% %22s %s" %
          (a, k, sn, sd, len(rs), len(bl), 100*hits/len(rs), roi, L.fmt_ci(lo, hi),
           "CLEARS" if roi >= CEIL else ""))
    seen.append(v)
best = max(seen)
beat = sum(1 for s in sims if s >= best)
print("\n  best real cell %+.2f%%   ceiling %+.2f%%   global permutation p = %.4f   cells clearing: %d/%d"
      % (best, CEIL, beat/Tn, sum(1 for v in seen if v >= CEIL), len(seen)))
