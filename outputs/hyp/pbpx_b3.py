"""Hypothesis B: base-rate confound check. Is the top-20% OVER edge just an always-over sample?"""
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
lg = statistics.mean(r["oreb_pct"] for r in rows if r["oreb_pct"] is not None)
byg = collections.defaultdict(dict)
for r in rows: byg[r["game_id"]][r["side"]] = r
G = []
for gid, sd in byg.items():
    h, a = sd.get("home"), sd.get("away")
    if not h or not a or h["n_prior"] < 5 or a["n_prior"] < 5: continue
    if None in (h["wf_orb"], h["wf_orb_all"], a["wf_orb"], a["wf_orb_all"]): continue
    mm = (h["wf_orb"] - lg) + (a["wf_orb_all"] - lg) + (a["wf_orb"] - lg) + (h["wf_orb_all"] - lg)
    G.append(dict(gid=gid, mm=mm, season=h["season"], total=h["total"], ou_o=h["ou_o"], ou_u=h["ou_u"],
                  gt=h["game_total"]))
G = [g for g in G if g["ou_o"] and g["ou_u"]]


def roi_over(sub):
    ps = [0.0 if g["gt"] == g["total"] else (g["ou_o"] - 1 if g["gt"] > g["total"] else -1) for g in sub]
    return sum(ps) / len(ps), ps


def roi_under(sub):
    ps = [0.0 if g["gt"] == g["total"] else (g["ou_u"] - 1 if g["gt"] < g["total"] else -1) for g in sub]
    return sum(ps) / len(ps), ps


mo, _ = roi_over(G); mu, _ = roi_under(G)
ov = sum(1 for g in G if g["gt"] > g["total"]); un = sum(1 for g in G if g["gt"] < g["total"])
print("BASE RATE over the whole B universe (n=%d games, 2023-2026):" % len(G))
print("  over hit %d / under %d / push %d  = over %.1f%%" % (ov, un, len(G) - ov - un, 100 * ov / (ov + un)))
print("  blind OVER  ROI %+.2f%%    blind UNDER ROI %+.2f%%   mean(actual - closing total) = %+.2f pts" %
      (100 * mo, 100 * mu, statistics.mean(g["gt"] - g["total"] for g in G)))
print("  --> ANY over-leaning cell inherits %+.2f%% for free. This is the Law-9 always-over base rate." % (100 * mo))
q = sorted(G, key=lambda g: g["mm"])
for tail in (0.10, 0.20, 0.30, 0.50):
    k = int(tail * len(q)); sel = q[-k:]; rest = q[:-k]
    m, ps = roi_over(sel); mr, _ = roi_over(rest)
    _, lo, hi = block_boot([[p] for p in ps], 6000, 9)
    print("  top %4.0f%% mm_sum: n=%3d  OVER ROI %+7.2f%% CI[%+.1f%%,%+.1f%%] | rest %+.2f%% | EXCESS over base %+.2f%%"
          % (100 * tail, len(sel), 100 * m, 100 * lo, 100 * hi, 100 * mr, 100 * (m - mo)))
print("\nby season, blind-over base rate vs top-20%% cell:")
for s in sorted(set(g["season"] for g in G)):
    sub = [g for g in G if g["season"] == s]
    if len(sub) < 60: continue
    k = int(0.20 * len(q))
    sel = [g for g in q[-k:] if g["season"] == s]
    b, _ = roi_over(sub)
    c = roi_over(sel)[0] if len(sel) >= 12 else None
    print("  %d n=%3d blind-over %+7.2f%% | cell n=%2d %s" %
          (s, len(sub), 100 * b, len(sel), ("%+7.2f%%" % (100 * c)) if c is not None else "  thin"))
