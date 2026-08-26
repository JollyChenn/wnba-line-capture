"""Hypothesis B, season-neutral: centre OREB rates on a WALK-FORWARD within-season league mean,
and rank the mismatch within season, so no season's rule-change drift dominates the tail."""
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

# walk-forward league OREB% within season
byseason = collections.defaultdict(list)
for r in rows:
    byseason[r["season"]].append(r)
for s, v in byseason.items():
    v.sort(key=lambda r: r["date"])
lgwf = {}
for s, v in byseason.items():
    co = cd = 0
    for r in v:
        lgwf[(r["game_id"], r["side"])] = (co / (co + cd)) if (co + cd) > 200 else None
        co += r["oreb"]; cd += r["opp_dreb"]
print("season league OREB%% (full-season, for reference):")
for s in sorted(byseason):
    v = byseason[s]
    print("  %d  %.4f  (n=%d team-games)" % (s, sum(r["oreb"] for r in v) / (sum(r["oreb"] for r in v) + sum(r["opp_dreb"] for r in v)), len(v)))

byg = collections.defaultdict(dict)
for r in rows: byg[r["game_id"]][r["side"]] = r
G = []
for gid, sd in byg.items():
    h, a = sd.get("home"), sd.get("away")
    if not h or not a or h["n_prior"] < 5 or a["n_prior"] < 5: continue
    if None in (h["wf_orb"], h["wf_orb_all"], a["wf_orb"], a["wf_orb_all"]): continue
    lg = lgwf.get((gid, "home"))
    if lg is None: continue
    mm = (h["wf_orb"] - lg) + (a["wf_orb_all"] - lg) + (a["wf_orb"] - lg) + (h["wf_orb_all"] - lg)
    if not (h["ou_o"] and h["ou_u"]): continue
    G.append(dict(gid=gid, mm=mm, season=h["season"], date=h["date"], total=h["total"],
                  ou_o=h["ou_o"], ou_u=h["ou_u"], gt=h["game_total"], resid=h["game_total"] - h["total"]))
print("\ngames: %d" % len(G))
# rank within season
for s in set(g["season"] for g in G):
    sub = sorted([g for g in G if g["season"] == s], key=lambda g: g["mm"])
    for i, g in enumerate(sub):
        g["pct"] = (i + 0.5) / len(sub)

b, se, t = ols([float(g["resid"]) for g in G], [[g["mm"]] for g in G])
print("(actual - closing total) ~ mm_sum(season-centred): slope %+.2f  t=%.2f  n=%d  [+1sd = %+.2f pts]" %
      (b[1], t[1], len(G), b[1] * statistics.pstdev(g["mm"] for g in G)))
b, se, t = ols([float(g["total"]) for g in G], [[g["mm"]] for g in G])
print("CLOSING total ~ mm_sum: slope %+.2f t=%.2f   [book still ignores it]" % (b[1], t[1]))


def roi(sub, side="o"):
    ps = []
    for g in sub:
        if g["gt"] == g["total"]: ps.append(0.0)
        elif side == "o": ps.append(g["ou_o"] - 1 if g["gt"] > g["total"] else -1)
        else: ps.append(g["ou_u"] - 1 if g["gt"] < g["total"] else -1)
    return sum(ps) / len(ps), ps


base, _ = roi(G)
print("blind OVER base ROI %+.2f%%" % (100 * base))
print("\n%-16s %6s %9s %20s %10s %s" % ("within-season tail", "n", "OVER ROI", "CI", "excess", "per-season ROI"))
for tail in (0.10, 0.20, 0.30):
    sel = [g for g in G if g["pct"] >= 1 - tail]
    m, ps = roi(sel)
    _, lo, hi = block_boot([[p] for p in ps], 6000, 21)
    per = []
    for s in sorted(set(g["season"] for g in sel)):
        ss = [g for g in sel if g["season"] == s]
        if len(ss) >= 12: per.append("%d:%+.1f%%(n=%d)" % (s, 100 * roi(ss)[0], len(ss)))
    print("%-16s %6d %+8.2f%% [%+6.1f%%,%+6.1f%%] %+9.2f%% %s" %
          ("top %.0f%%" % (100 * tail), len(sel), 100 * m, 100 * lo, 100 * hi, 100 * (m - base), " ".join(per)))
# permutation p for the pre-specified top-20% cell (game block: shuffle mm across games within season)
sel = [g for g in G if g["pct"] >= 0.80]
m0 = roi(sel)[0]
rnd = random.Random(20260826); N = 4000; nb = 0
byS = collections.defaultdict(list)
for g in G: byS[g["season"]].append(g)
for _ in range(N):
    pick = []
    for s, v in byS.items():
        k = int(round(0.20 * len(v)))
        pick += rnd.sample(v, k)
    if roi(pick)[0] >= m0: nb += 1
print("\npre-specified top-20%% within-season cell: n=%d ROI %+.2f%%  permutation p=%.4f" % (len(sel), 100 * m0, nb / N))
# OOS: fit nothing, but hold out last season
tr = [g for g in G if g["season"] <= 2025]
te = [g for g in G if g["season"] == 2026]
for lab, sub in (("2023-2025", tr), ("2026 holdout", te)):
    s2 = [g for g in sub if g["pct"] >= 0.80]
    if len(s2) >= 12:
        print("  %-13s cell n=%3d ROI %+7.2f%%  (blind over %+.2f%%)" % (lab, len(s2), 100 * roi(s2)[0], 100 * roi(sub)[0]))
