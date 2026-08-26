"""Hypothesis B, DEFINITIVE. Strictly walk-forward:
   - league OREB% baseline = season-to-date only
   - the selection threshold = percentile of mm among games ALREADY PLAYED this season (>=60)
   - declared grid + game-block noise ceiling computed before reading the table
"""
import csv, os, sys, math, collections, random, statistics
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pbpx_lib import *

rows = load_master(require_recon=True)
S = series(rows)
for k, v in S.items():
    for i, r in enumerate(v):
        pri = v[:i]
        r["n_prior"] = len(pri)
        if not pri:
            r["wf_orb"] = r["wf_orb_all"] = None
            continue
        o = sum(p["oreb"] for p in pri); od = sum(p["opp_dreb"] for p in pri)
        r["wf_orb"] = o / (o + od) if (o + od) else None
        oo = sum(p["opp_oreb"] for p in pri); dd = sum(p["dreb"] for p in pri)
        r["wf_orb_all"] = oo / (oo + dd) if (oo + dd) else None

byseason = collections.defaultdict(list)
for r in rows: byseason[r["season"]].append(r)
for s, v in byseason.items(): v.sort(key=lambda r: r["date"])
lgwf = {}
for s, v in byseason.items():
    co = cd = 0
    for r in v:
        lgwf[(r["game_id"], r["side"])] = (co / (co + cd)) if (co + cd) > 200 else None
        co += r["oreb"]; cd += r["opp_dreb"]

byg = collections.defaultdict(dict)
for r in rows: byg[r["game_id"]][r["side"]] = r
G = []
for gid, sd in byg.items():
    h, a = sd.get("home"), sd.get("away")
    if not h or not a or h["n_prior"] < 5 or a["n_prior"] < 5: continue
    if None in (h["wf_orb"], h["wf_orb_all"], a["wf_orb"], a["wf_orb_all"]): continue
    lg = lgwf.get((gid, "home"))
    if lg is None or not (h["ou_o"] and h["ou_u"]): continue
    mm = (h["wf_orb"] - lg) + (a["wf_orb_all"] - lg) + (a["wf_orb"] - lg) + (h["wf_orb_all"] - lg)
    G.append(dict(gid=gid, mm=mm, season=h["season"], date=h["date"], total=h["total"],
                  ou_o=h["ou_o"], ou_u=h["ou_u"], gt=h["game_total"]))
G.sort(key=lambda g: (g["season"], g["date"]))

# strictly walk-forward percentile: rank mm against mm of games already played THIS season
hist = collections.defaultdict(list)
for g in G:
    h = hist[g["season"]]
    g["wf_pct"] = (sum(1 for x in h if x < g["mm"]) / len(h)) if len(h) >= 60 else None
    h.append(g["mm"])
W = [g for g in G if g["wf_pct"] is not None]
print("games with a strictly walk-forward percentile: %d of %d  (seasons %s)" %
      (len(W), len(G), sorted(collections.Counter(g["season"] for g in W).items())))

TAILS = (0.10, 0.20, 0.30)
SIDES = ("over", "under")
GRID = [(t, s) for t in TAILS for s in SIDES]
print("GRID DECLARED: %d cells = tail%s x side%s ; independent unit = the GAME" % (len(GRID), TAILS, SIDES))


def prof(g, side):
    if g["gt"] == g["total"]: return 0.0
    if side == "over": return g["ou_o"] - 1 if g["gt"] > g["total"] else -1.0
    return g["ou_u"] - 1 if g["gt"] < g["total"] else -1.0


def cell(pcts, c):
    t, side = c
    thr = 1 - t
    sel = [g for g, p in zip(W, pcts) if (p >= thr if side == "over" else p <= t)]
    return sel


def evaluate(pcts):
    best = None
    tab = []
    for c in GRID:
        sel = cell(pcts, c)
        if len(sel) < 30:
            tab.append((c, len(sel), None)); continue
        ps = [prof(g, c[1]) for g in sel]
        roi = sum(ps) / len(ps)
        tab.append((c, len(sel), roi))
        if best is None or roi > best[0]: best = (roi, c, len(sel))
    return best, tab


真 = [g["wf_pct"] for g in W]
rnd = random.Random(20260826)
nulls = []
NP = 500
for _ in range(NP):
    # game-block permutation: shuffle the walk-forward percentiles across games WITHIN season
    byS = collections.defaultdict(list)
    for i, g in enumerate(W): byS[g["season"]].append(i)
    pp = list(真)
    for s, idxs in byS.items():
        vals = [真[i] for i in idxs]
        rnd.shuffle(vals)
        for i, v in zip(idxs, vals): pp[i] = v
    b, _ = evaluate(pp)
    if b: nulls.append(b[0])
nulls.sort()
p95 = nulls[int(0.95 * len(nulls))]
print("NOISE CEILING (within-season game-block permutation, %d perms): best-of-%d ROI median %+.2f%%, p95 %+.2f%%"
      % (NP, len(GRID), 100 * nulls[len(nulls) // 2], 100 * p95))

blind_o = statistics.mean(prof(g, "over") for g in W)
blind_u = statistics.mean(prof(g, "under") for g in W)
print("blind base rates on this universe: OVER %+.2f%%  UNDER %+.2f%%  (over hit %.1f%%)" %
      (100 * blind_o, 100 * blind_u, 100 * sum(1 for g in W if g["gt"] > g["total"]) / len(W)))

best, tab = evaluate(真)
print("\n%-18s %5s %10s %22s %9s" % ("cell", "n", "ROI", "block-boot CI", "clears?"))
for c, n, roi in tab:
    if roi is None:
        print("%-18s %5d %10s" % (str(c), n, "--thin--")); continue
    sel = cell(真, c); ps = [prof(g, c[1]) for g in sel]
    _, lo, hi = block_boot([[p] for p in ps], 4000, 31)
    print("%-18s %5d %+9.2f%% [%+7.2f%%,%+7.2f%%] %9s" % (str(c), n, 100 * roi, 100 * lo, 100 * hi,
                                                          "CLEARS" if roi > p95 else ""))
print("\nBEST %s n=%d ROI %+.2f%% vs ceiling %+.2f%% -> %s" %
      (best[1], best[2], 100 * best[0], 100 * p95, "CLEARS CEILING" if best[0] > p95 else "UNDER CEILING (not a finding)"))
for c in GRID:
    sel = cell(真, c)
    if len(sel) < 30: continue
    per = []
    for s in sorted(set(g["season"] for g in sel)):
        ss = [g for g in sel if g["season"] == s]
        if len(ss) >= 10: per.append("%d:%+.0f%%(n=%d)" % (s, 100 * statistics.mean(prof(g, c[1]) for g in ss), len(ss)))
    print("  %-18s %s" % (str(c), " ".join(per)))
