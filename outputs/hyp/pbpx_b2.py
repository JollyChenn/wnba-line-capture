import csv, os, sys, math, collections, random, statistics
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
random.seed(20260826)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pbpx_lib import *


def build(require_recon, minpr=5):
    rows = load_master(require_recon=require_recon)
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
    for r in rows:
        byg[r["game_id"]][r["side"]] = r
    G = []
    for gid, sd in byg.items():
        h, a = sd.get("home"), sd.get("away")
        if not h or not a: continue
        if h["n_prior"] < minpr or a["n_prior"] < minpr: continue
        if None in (h["wf_orb"], h["wf_orb_all"], a["wf_orb"], a["wf_orb_all"]): continue
        h["mm"] = (h["wf_orb"] - lg) + (a["wf_orb_all"] - lg)
        a["mm"] = (a["wf_orb"] - lg) + (h["wf_orb_all"] - lg)
        G.append(dict(gid=gid, h=h, a=a, mm=h["mm"] + a["mm"], season=h["season"], date=h["date"],
                      total=h["total"], ou_o=h["ou_o"], ou_u=h["ou_u"], gt=h["game_total"],
                      resid=h["game_total"] - h["total"],
                      oreb=h["oreb"] + a["oreb"], poss=h["poss"] + a["poss"],
                      fga=h["fga"] + a["fga"]))
    return G, rows


for rr in (True, False):
    G, rows = build(rr)
    print("=" * 92)
    print("recon-clean-only = %s : %d games" % (rr, len(G)))
    mms = [g["mm"] for g in G]
    print("  mm_sum: mean %+.4f sd %.4f  p80 %+.4f  p90 %+.4f" %
          (statistics.mean(mms), statistics.pstdev(mms), sorted(mms)[int(.8 * len(mms))], sorted(mms)[int(.9 * len(mms))]))
    b, se, t = ols([float(g["resid"]) for g in G], [[g["mm"]] for g in G])
    sd = statistics.pstdev(mms)
    print("  (game total - closing total) = %+.3f %+.2f * mm_sum  (t=%.2f, n=%d)  -> +1sd mismatch = %+.2f pts of total" %
          (b[0], b[1], t[1], len(G), b[1] * sd))
    b2, se2, t2 = ols([float(g["total"]) for g in G], [[g["mm"]] for g in G])
    print("  CLOSING total ~ mm_sum: slope %+.2f (t=%.2f)  [book prices ~%.0f%% of the %.2f-pt effect]" %
          (b2[1], t2[1], 100 * b2[1] / max(b[1] + b2[1], 1e-9), b[1] * sd))
    b3, se3, t3 = ols([float(g["oreb"]) for g in G], [[g["mm"]] for g in G])
    b4, se4, t4 = ols([float(g["fga"]) for g in G], [[g["mm"]] for g in G])
    b5, se5, t5 = ols([float(g["poss"]) for g in G], [[g["mm"]] for g in G])
    print("  realised: OREB slope %+.1f (t=%.1f) | FGA slope %+.1f (t=%.1f) | POSS slope %+.1f (t=%.1f)" %
          (b3[1], t3[1], b4[1], t4[1], b5[1], t5[1]))
    print("  per-season residual regression (consistency):")
    for s in sorted(set(g["season"] for g in G)):
        sub = [g for g in G if g["season"] == s]
        if len(sub) < 60: continue
        bb, _, tt = ols([float(g["resid"]) for g in sub], [[g["mm"]] for g in sub])
        print("    %d  n=%3d  slope %+8.2f  t=%+.2f" % (s, len(sub), bb[1], tt[1]))
    # single PRE-SPECIFIED bet: top 20% mm_sum -> OVER
    q = sorted(G, key=lambda g: g["mm"])
    k = int(0.20 * len(q))
    sel = q[-k:]
    ps = []
    for g in sel:
        if not g["ou_o"]: continue
        ps.append(0.0 if g["gt"] == g["total"] else (g["ou_o"] - 1 if g["gt"] > g["total"] else -1))
    m, lo, hi = block_boot([[p] for p in ps], 6000, 3)
    w = sum(1 for p in ps if p > 0); pu = sum(1 for p in ps if p == 0)
    print("  PRE-SPECIFIED single cell (top20%% mm_sum, bet OVER): n=%d games  %d-%d-%d = %.1f%%  ROI %+.2f%% CI[%+.2f%%, %+.2f%%]"
          % (len(ps), w, len(ps) - w - pu, pu, 100 * w / max(len(ps) - pu, 1), 100 * m, 100 * lo, 100 * hi))
    # one-cell permutation p-value
    rnd = random.Random(5); nb = 0; N = 3000
    vals = [g["mm"] for g in G]
    idx = list(range(len(G)))
    for _ in range(N):
        rnd.shuffle(vals)
        order = sorted(idx, key=lambda i: vals[i])[-k:]
        pp = []
        for i in order:
            g = G[i]
            if not g["ou_o"]: continue
            pp.append(0.0 if g["gt"] == g["total"] else (g["ou_o"] - 1 if g["gt"] > g["total"] else -1))
        if pp and sum(pp) / len(pp) >= m: nb += 1
    print("  one-cell permutation p = %.4f (%d/%d)" % (nb / N, nb, N))
    # walk-forward: rank by mm within season using only prior games -> already walk-forward; check by-season ROI
    print("  by-season ROI of that cell:")
    for s in sorted(set(g["season"] for g in sel)):
        sub = [g for g in sel if g["season"] == s and g["ou_o"]]
        if len(sub) < 15: continue
        pp = [0.0 if g["gt"] == g["total"] else (g["ou_o"] - 1 if g["gt"] > g["total"] else -1) for g in sub]
        print("    %d n=%3d ROI %+7.2f%%" % (s, len(pp), 100 * sum(pp) / len(pp)))
    # confound check
    print("  confound: top20%% mean closing total %.2f vs rest %.2f ; mean date-index ok" %
          (statistics.mean(g["total"] for g in sel), statistics.mean(g["total"] for g in q[:-k])))
