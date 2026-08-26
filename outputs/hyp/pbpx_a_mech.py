import csv, os, sys, math, collections, random, statistics
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
random.seed(20260826)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pbpx_lib import *

rows = load_master()
S = series(rows)
print("team-games %d, games %d, team-seasons %d" % (len(rows), len(set(r["game_id"] for r in rows)), len(S)))
print("seasons:", sorted(collections.Counter(r["season"] for r in rows).items()))

MINPR = 5
for k, v in S.items():
    for i, r in enumerate(v):
        pri = [p for p in v[:i] if p["tpa"] >= 5]
        r["n_prior"] = len(pri)
        r["z3"] = None
        if len(pri) >= MINPR and r["tp_pct"] is not None:
            r["base_pct"] = sum(p["tpm"] for p in pri) / sum(p["tpa"] for p in pri)
            sd = statistics.pstdev([p["tp_pct"] for p in pri])
            r["z3"] = (r["tp_pct"] - r["base_pct"]) / sd if sd > 0 else None
            r["base_tot"] = statistics.mean(p["total"] for p in pri)
            r["base_pts"] = statistics.mean(p["pts"] for p in pri)
            r["base_gt"] = statistics.mean(p["game_total"] for p in pri)
        r["nxt"] = v[i + 1] if i + 1 < len(v) else None

E = [r for r in rows if r.get("z3") is not None and r["nxt"] is not None and r["nxt"].get("z3") is not None]
print("\nusable team-games (z3 + next game with baseline): %d  (%d games)" % (len(E), len(set(r["game_id"] for r in E))))
zs = [r["z3"] for r in E]
print("z3: mean %.3f sd %.3f  P(z>=1.5)=%.3f  P(z>=2)=%.3f  P(z>=2.5)=%.3f" %
      (statistics.mean(zs), statistics.pstdev(zs),
       sum(1 for z in zs if z >= 1.5) / len(zs), sum(1 for z in zs if z >= 2) / len(zs),
       sum(1 for z in zs if z >= 2.5) / len(zs)))
print("mean team 3PA/game %.1f  3P%% %.3f" % (statistics.mean(r["tpa"] for r in E), statistics.mean(r["tp_pct"] for r in E)))

print("\n=== MECHANISM 1: does a hot 3P game predict a LOWER 3P%% next game? ===")
y = [r["nxt"]["tp_pct"] - r["nxt"]["base_pct"] for r in E]
X = [[r["z3"]] for r in E]
b, se, t = ols(y, X)
print("  next-game 3P%% deviation-from-own-baseline = %+.5f %+.5f * z3   (t=%.2f, n=%d)" % (b[0], b[1], t[1], len(E)))
print("  -> 1sd hotter this game shifts NEXT game 3P%% by %+.3f pp. 0.00 = complete regression to the mean." % (100 * b[1]))
y2 = [r["nxt"]["tp_pct"] for r in E]
b2, se2, t2 = ols(y2, [[r["tp_pct"]] for r in E])
print("  raw AR(1) of team 3P%%: slope %+.4f (t=%.2f)  [0 = no carryover]" % (b2[1], t2[1]))
print("  %-13s %5s  %8s %8s   %9s %8s %8s" % ("bucket", "n", "this3P%", "own base", "next3P%", "nxtbase", "nxt dev"))
for lo, hi, lab in ((2.5, 99, "z>=2.5"), (2.0, 99, "z>=2.0 HOT"), (1.5, 2.0, "z 1.5-2.0"),
                    (-0.5, 0.5, "z ~0"), (-2.0, -1.5, "z -2..-1.5"), (-99, -2.0, "z<=-2 COLD")):
    sub = [r for r in E if lo <= r["z3"] < hi]
    if len(sub) < 15:
        continue
    print("  %-13s %5d  %8.3f %8.3f   %9.3f %8.3f %+8.4f" % (
        lab, len(sub), statistics.mean(r["tp_pct"] for r in sub), statistics.mean(r["base_pct"] for r in sub),
        statistics.mean(r["nxt"]["tp_pct"] for r in sub), statistics.mean(r["nxt"]["base_pct"] for r in sub),
        statistics.mean(r["nxt"]["tp_pct"] - r["nxt"]["base_pct"] for r in sub)))

print("\n=== MECHANISM 2: does the market's NEXT-game total RISE after a hot game? ===")
tot_by_ts = {}
for k, v in S.items():
    tot_by_ts[k] = v


def opp_std_avg(season, opp, date):
    v = tot_by_ts.get((season, opp))
    if not v:
        return None
    pri = [p for p in v if p["date"] < date]
    return statistics.mean(p["total"] for p in pri) if len(pri) >= 5 else None


for r in E:
    nx = r["nxt"]
    ob = opp_std_avg(nx["season"], nx["opp"], nx["date"])
    r["nxt_opp_base"] = ob
    r["nxt_tot_dev"] = (nx["total"] - 0.5 * (nx["base_tot"] + ob)) if ob is not None else None
E2 = [r for r in E if r["nxt_tot_dev"] is not None]
b, se, t = ols([r["nxt_tot_dev"] for r in E2], [[r["z3"]] for r in E2])
print("  next total minus (team+opp season-to-date avg total)/1 = %+.3f %+.4f * z3   (t=%.2f, n=%d)" % (b[0], b[1], t[1], len(E2)))
b, se, t = ols([r["nxt"]["total"] - r["total"] for r in E], [[r["z3"]] for r in E])
print("  raw total CHANGE (next total - this total)             = %+.3f %+.4f * z3   (t=%.2f, n=%d)" % (b[0], b[1], t[1], len(E)))
print("  %-13s %5s  %10s %12s  %10s" % ("bucket", "n", "nxt-tot dev", "nxt tot raw", "tot change"))
for lo, hi, lab in ((2.5, 99, "z>=2.5"), (2.0, 99, "z>=2.0 HOT"), (1.5, 99, "z>=1.5"),
                    (-0.5, 0.5, "z ~0"), (-99, -1.5, "z<=-1.5 COLD")):
    sub = [r for r in E2 if lo <= r["z3"] < hi]
    if len(sub) < 15:
        continue
    print("  %-13s %5d  %+10.3f %12.2f  %+10.3f" % (
        lab, len(sub), statistics.mean(r["nxt_tot_dev"] for r in sub),
        statistics.mean(r["nxt"]["total"] for r in sub),
        statistics.mean(r["nxt"]["total"] - r["total"] for r in sub)))

print("\n  SANITY controls (do totals move at all in response to recent production?)")
for r in E2:
    r["pts_dev"] = r["pts"] - r["base_pts"]
    r["gt_dev"] = r["game_total"] - r["base_gt"]
b, se, t = ols([r["nxt_tot_dev"] for r in E2], [[r["pts_dev"]] for r in E2])
print("    vs (this game team pts - own season avg pts)   slope %+.4f (t=%.2f)" % (b[1], t[1]))
b, se, t = ols([r["nxt_tot_dev"] for r in E2], [[r["gt_dev"]] for r in E2])
print("    vs (this game GAME total - own season avg)     slope %+.4f (t=%.2f)" % (b[1], t[1]))
b, se, t = ols([r["nxt"]["total"] - r["total"] for r in E2], [[r["gt_dev"]] for r in E2])
print("    raw total change vs game-total surprise        slope %+.4f (t=%.2f)" % (b[1], t[1]))
b, se, t = ols([r["nxt_tot_dev"] for r in E2], [[r["z3"], r["gt_dev"]] for r in E2])
print("    MULTIVARIATE next_tot_dev ~ z3 + gt_dev: z3 %+.4f (t=%.2f), gt_dev %+.4f (t=%.2f)" % (b[1], t[1], b[2], t[2]))

import pickle
with open(os.path.join(H, "pbpx_a_rows.pkl"), "wb") as fh:
    pickle.dump([{k: v for k, v in r.items() if k not in ("nxt", "tskey")} | {"nxt_gid": r["nxt"]["game_id"] if r["nxt"] else None} for r in rows], fh)
print("\nsaved pbpx_a_rows.pkl")
