import csv, os, sys, math, collections, random, statistics
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
random.seed(20260826)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pbpx_lib import *

rows = load_master()
S = series(rows)
print("universe: %d team-games / %d games / seasons %s" %
      (len(rows), len(set(r["game_id"] for r in rows)), sorted(set(r["season"] for r in rows))))

# ---- walk-forward team OREB% (own OREB / own missed FG chances) and OREB% ALLOWED
MINPR = 5
for k, v in S.items():
    for i, r in enumerate(v):
        pri = v[:i]
        r["wf_ok"] = len(pri) >= MINPR
        r["n_prior"] = len(pri)
        if not pri:
            continue
        o = sum(p["oreb"] for p in pri)
        od = sum(p["opp_dreb"] for p in pri)
        r["wf_orb"] = o / (o + od) if (o + od) else None            # own offensive rebound rate
        oo = sum(p["opp_oreb"] for p in pri)
        dd = sum(p["dreb"] for p in pri)
        r["wf_orb_all"] = oo / (oo + dd) if (oo + dd) else None      # rate ALLOWED to opponents
        r["wf_3ar"] = sum(p["tpa"] for p in pri) / max(sum(p["fga"] for p in pri), 1)
        r["wf_poss"] = statistics.mean(p["poss"] for p in pri)

byg = collections.defaultdict(dict)
for r in rows:
    byg[r["game_id"]][r["side"]] = r

lg_orb = statistics.mean(r["oreb_pct"] for r in rows if r["oreb_pct"] is not None)
print("league OREB%% (parsed) = %.4f ; league 3PA rate = %.3f" %
      (lg_orb, sum(r["tpa"] for r in rows) / sum(r["fga"] for r in rows)))

G = []
for gid, sd in byg.items():
    h, a = sd.get("home"), sd.get("away")
    if not h or not a:
        continue
    if not (h["wf_ok"] and a["wf_ok"]):
        continue
    if None in (h["wf_orb"], h["wf_orb_all"], a["wf_orb"], a["wf_orb_all"]):
        continue
    # mismatch for each side: own crash rate + opponent's leakiness, centred
    h["mm"] = (h["wf_orb"] - lg_orb) + (a["wf_orb_all"] - lg_orb)
    a["mm"] = (a["wf_orb"] - lg_orb) + (h["wf_orb_all"] - lg_orb)
    G.append(dict(gid=gid, h=h, a=a, mm_sum=h["mm"] + a["mm"], mm_dif=h["mm"] - a["mm"],
                  total=h["total"], ou_o=h["ou_o"], ou_u=h["ou_u"], gt=h["game_total"],
                  spread=h["spread"], sp_h=h["sp_h"], sp_a=h["sp_a"],
                  hm=h["margin"], season=h["season"], date=h["date"]))
print("games with both sides walk-forward ready: %d" % len(G))
TG = [r for g in G for r in (g["h"], g["a"])]

print("\n=== MECHANISM 1: does the walk-forward mismatch predict REALISED offensive rebounding? ===")
b, se, t = ols([r["oreb_pct"] for r in TG], [[r["mm"]] for r in TG])
print("  realised OREB%% = %+.4f %+.4f * mismatch   (t=%.2f, n=%d)" % (b[0], b[1], t[1], len(TG)))
b, se, t = ols([float(r["oreb"]) for r in TG], [[r["mm"]] for r in TG])
print("  realised OREB count = %+.2f %+.2f * mismatch  (t=%.2f)  -> a +10pp mismatch buys %+.2f extra boards" % (b[0], b[1], t[1], 0.10 * b[1]))
q = sorted(TG, key=lambda r: r["mm"])
n4 = len(q) // 4
for lab, sub in (("bottom 25%%", q[:n4]), ("mid", q[n4:-n4]), ("top 25%%", q[-n4:])):
    print("    %-11s n=%4d  mismatch %+.4f -> realised OREB%% %.4f  OREB %.2f  poss %.1f  pts %.1f" %
          (lab, len(sub), statistics.mean(r["mm"] for r in sub), statistics.mean(r["oreb_pct"] for r in sub),
           statistics.mean(r["oreb"] for r in sub), statistics.mean(r["poss"] for r in sub),
           statistics.mean(r["pts"] for r in sub)))

print("\n=== MECHANISM 2: does the mismatch predict points/possessions BEYOND the line? ===")
b, se, t = ols([float(g["gt"] - g["total"]) for g in G], [[g["mm_sum"]] for g in G])
print("  (game total - CLOSING total)  = %+.3f %+.3f * mm_sum   (t=%.2f, n=%d)" % (b[0], b[1], t[1], len(G)))
b, se, t = ols([float(g["hm"] + (g["spread"] if g["spread"] is not None else 0)) for g in G if g["spread"] is not None],
               [[g["mm_dif"]] for g in G if g["spread"] is not None])
print("  (home margin - home spread cover) = %+.3f %+.3f * mm_dif  (t=%.2f)" % (b[0], b[1], t[1]))
b, se, t = ols([g["h"]["poss"] + g["a"]["poss"] for g in G], [[g["mm_sum"]] for g in G])
print("  realised game possessions = %+.2f %+.2f * mm_sum  (t=%.2f)" % (b[0], b[1], t[1]))
print("  -- is the mismatch already IN the line? --")
b, se, t = ols([float(g["total"]) for g in G], [[g["mm_sum"]] for g in G])
print("  CLOSING total = %+.2f %+.2f * mm_sum  (t=%.2f)  [if >0 the book already prices it]" % (b[0], b[1], t[1]))
b, se, t = ols([float(g["spread"]) for g in G if g["spread"] is not None], [[g["mm_dif"]] for g in G if g["spread"] is not None])
print("  CLOSING home spread = %+.2f %+.2f * mm_dif  (t=%.2f)" % (b[0], b[1], t[1]))

# ---------------- BET GRID, DECLARED FIRST ----------------
QS = (0.10, 0.20, 0.30)
MPS = (5, 10)
MKT = ("total_over", "total_under", "spread_high", "spread_low")
GRIDC = [(q, m, k) for q in QS for m in MPS for k in MKT]
print("\nGRID: %d cells = tail%s x min_prior%s x market%s" % (len(GRIDC), QS, MPS, MKT))


def build(minpr):
    out = []
    for g in G:
        if g["h"]["n_prior"] < minpr or g["a"]["n_prior"] < minpr:
            continue
        out.append(g)
    return out


def cell_bets(cell, key_sum, key_dif):
    qq, mp, mk = cell
    pool = build(mp)
    if len(pool) < 40:
        return []
    if mk.startswith("total"):
        vals = sorted(key_sum[g["gid"]] for g in pool)
        k = max(int(qq * len(vals)), 1)
        hi = vals[-k]
        lo = vals[k - 1]
        res = []
        for g in pool:
            v = key_sum[g["gid"]]
            if mk == "total_over" and v >= hi and g["ou_o"]:
                p = 0.0 if g["gt"] == g["total"] else (g["ou_o"] - 1 if g["gt"] > g["total"] else -1)
                res.append((g["gid"], p))
            elif mk == "total_under" and v <= lo and g["ou_u"]:
                p = 0.0 if g["gt"] == g["total"] else (g["ou_u"] - 1 if g["gt"] < g["total"] else -1)
                res.append((g["gid"], p))
        return res
    else:
        pool = [g for g in pool if g["spread"] is not None and g["sp_h"] and g["sp_a"]]
        vals = sorted(key_dif[g["gid"]] for g in pool)
        k = max(int(qq * len(vals)), 1)
        hi = vals[-k]
        lo = vals[k - 1]
        res = []
        for g in pool:
            v = key_dif[g["gid"]]
            cov = g["hm"] + g["spread"]
            if mk == "spread_high" and v >= hi:
                p = 0.0 if abs(cov) < 1e-9 else (g["sp_h"] - 1 if cov > 0 else -1)
                res.append((g["gid"], p))
            elif mk == "spread_low" and v <= lo:
                cova = -cov
                p = 0.0 if abs(cova) < 1e-9 else (g["sp_a"] - 1 if cova > 0 else -1)
                res.append((g["gid"], p))
        return res


ks = {g["gid"]: g["mm_sum"] for g in G}
kd = {g["gid"]: g["mm_dif"] for g in G}


def evaluate(ks, kd):
    best = None
    tab = []
    for c in GRIDC:
        bs = cell_bets(c, ks, kd)
        if len(bs) < 30:
            tab.append((c, len(bs), None))
            continue
        roi = sum(p for _, p in bs) / len(bs)
        tab.append((c, len(bs), roi))
        if best is None or roi > best[0]:
            best = (roi, c, len(bs))
    return best, tab


NPERM = 300
rnd = random.Random(20260826)
gids = [g["gid"] for g in G]
nulls = []
for _ in range(NPERM):
    sv = [ks[g] for g in gids]
    dv = [kd[g] for g in gids]
    rnd.shuffle(sv)
    rnd.shuffle(dv)
    b, _ = evaluate(dict(zip(gids, sv)), dict(zip(gids, dv)))
    if b:
        nulls.append(b[0])
nulls.sort()
p95 = nulls[int(0.95 * len(nulls))]
print("NOISE CEILING (game-block permutation of the mismatch, %d perms): best-of-%d ROI median %+.2f%%, p95 = %+.2f%%"
      % (NPERM, len(GRIDC), 100 * nulls[len(nulls) // 2], 100 * p95))

best, tab = evaluate(ks, kd)
print("\n%-30s %7s %9s %s" % ("cell (tail,minprior,market)", "n_games", "ROI", "clears?"))
for c, n, roi in tab:
    print("%-30s %7d %s %s" % (str(c), n, ("%+8.2f%%" % (100 * roi)) if roi is not None else "  --thin--",
                               "CLEARS" if (roi is not None and roi > p95) else ""))
print("\nBEST CELL %s n=%d ROI %+.2f%% vs ceiling %+.2f%% -> %s" %
      (best[1], best[2], 100 * best[0], 100 * p95, "CLEARS" if best[0] > p95 else "UNDER CEILING (not a finding)"))
for c in ((0.20, 5, "total_over"), (0.20, 5, "spread_high")):
    bs = cell_bets(c, ks, kd)
    m, lo, hi = block_boot([[p] for _, p in bs], 4000, 11)
    print("  %s: n=%d games ROI %+.2f%% CI[%+.2f%%, %+.2f%%]" % (str(c), len(bs), 100 * m, 100 * lo, 100 * hi))
