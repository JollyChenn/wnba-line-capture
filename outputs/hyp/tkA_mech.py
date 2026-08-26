# PART A - MECHANISM: is the CLOSING line's error larger early in the season?
import os, sys, math, statistics, collections, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
from tk_lib import load_games, annotate, devig2

G = annotate(load_games())
print("games loaded:", len(G))

# --- vig audit (breakeven) ---
for nm, a, b in [("ML", "ml_h", "ml_a"), ("SPREAD", "sp_h", "sp_a"), ("TOTAL", "ou_o", "ou_u")]:
    ov = [1/g[a] + 1/g[b] for g in G if g[a] and g[b]]
    print(f"  {nm:7s} n={len(ov)} mean overround={statistics.mean(ov):.4f}  breakeven={statistics.mean(ov)/2:.4f}")

# --- team-game-index distribution (playoff contamination check) ---
mx = collections.Counter()
for g in G:
    mx[(g["season"], g["home"])] = max(mx[(g["season"], g["home"])], g["tgi_h"])
    mx[(g["season"], g["away"])] = max(mx[(g["season"], g["away"])], g["tgi_a"])
print("  max team-game-index per season:", {s: max(v for (ss,t),v in mx.items() if ss==s) for s in sorted(set(k[0] for k in mx))})

def wkbucket(g):
    w = g["wk"]
    if w <= 3: return "wk1-3"
    if w <= 6: return "wk4-6"
    if w <= 10: return "wk7-10"
    if w <= 14: return "wk11-14"
    return "wk15+"
ORD = ["wk1-3", "wk4-6", "wk7-10", "wk11-14", "wk15+"]

def tgibucket(g, side):
    i = g["tgi_h"] if side == "h" else g["tgi_a"]
    if i <= 5: return "g1-5"
    if i <= 10: return "g6-10"
    if i <= 20: return "g11-20"
    if i <= 34: return "g21-34"
    return "g35+"
TORD = ["g1-5", "g6-10", "g11-20", "g21-34", "g35+"]

def tstat_diff(a, b):
    if len(a) < 3 or len(b) < 3: return float("nan")
    ma, mb = statistics.mean(a), statistics.mean(b)
    va, vb = statistics.pvariance(a), statistics.pvariance(b)
    se = math.sqrt(va/len(a) + vb/len(b))
    return (ma - mb)/se if se else float("nan")

print("\n=== MECHANISM 1: absolute closing-line error by league-week bucket ===")
rows = collections.defaultdict(lambda: collections.defaultdict(list))
for g in G:
    b = wkbucket(g)
    if g["spread"] is not None:
        rows["|spread err|"][b].append(abs(g["margin"] + g["spread"]))
        rows["signed spread err (home)"][b].append(g["margin"] + g["spread"])
    if g["total"] is not None:
        rows["|total err|"][b].append(abs(g["gtot"] - g["total"]))
        rows["signed total err (over)"][b].append(g["gtot"] - g["total"])
    p = devig2(g["ml_h"], g["ml_a"])
    if p is not None:
        y = 1.0 if g["margin"] > 0 else 0.0
        rows["ML brier"][b].append((p - y) ** 2)
        rows["ML signed (home-fav bias)"][b].append(y - p)

for met in ["|spread err|", "|total err|", "ML brier", "signed spread err (home)", "signed total err (over)", "ML signed (home-fav bias)"]:
    d = rows[met]
    line = f"{met:28s}"
    for b in ORD:
        v = d.get(b, [])
        line += f"  {b}={statistics.mean(v):+7.3f}(n={len(v):4d})" if v else f"  {b}=   --      "
    early = d.get("wk1-3", [])
    rest = [x for b in ORD[1:] for x in d.get(b, [])]
    line += f"   | wk1-3 vs rest t={tstat_diff(early, rest):+5.2f}"
    print(line)

print("\n=== MECHANISM 1b: same, by TEAM-game-index (per team-night, both teams pooled) ===")
r2 = collections.defaultdict(lambda: collections.defaultdict(list))
for g in G:
    for side in ("h", "a"):
        b = tgibucket(g, side)
        if g["spread"] is not None:
            r2["|spread err|"][b].append(abs(g["margin"] + g["spread"]))
        if g["total"] is not None:
            r2["|total err|"][b].append(abs(g["gtot"] - g["total"]))
for met in ["|spread err|", "|total err|"]:
    d = r2[met]
    line = f"{met:28s}"
    for b in TORD:
        v = d.get(b, [])
        line += f"  {b}={statistics.mean(v):+7.3f}(n={len(v):4d})" if v else f"  {b}=   --  "
    early = d.get("g1-5", [])
    rest = [x for b in TORD[1:] for x in d.get(b, [])]
    line += f"   | g1-5 vs rest t={tstat_diff(early, rest):+5.2f}"
    print(line)

print("\n=== MECHANISM 1c: per-season wk1-3 vs rest, |spread err| and |total err| ===")
print(f"{'season':8s} {'n_e':>4s} {'sp_e':>7s} {'sp_r':>7s} {'d':>7s} {'tot_e':>7s} {'tot_r':>7s} {'d':>7s}")
for s in sorted(set(g["season"] for g in G)):
    E = [g for g in G if g["season"] == s and g["wk"] <= 3]
    R = [g for g in G if g["season"] == s and g["wk"] > 3]
    se = [abs(g["margin"]+g["spread"]) for g in E if g["spread"] is not None]
    sr = [abs(g["margin"]+g["spread"]) for g in R if g["spread"] is not None]
    te = [abs(g["gtot"]-g["total"]) for g in E if g["total"] is not None]
    tr = [abs(g["gtot"]-g["total"]) for g in R if g["total"] is not None]
    print(f"{s:<8d} {len(se):4d} {statistics.mean(se):7.3f} {statistics.mean(sr):7.3f} {statistics.mean(se)-statistics.mean(sr):+7.3f} "
          f"{statistics.mean(te):7.3f} {statistics.mean(tr):7.3f} {statistics.mean(te)-statistics.mean(tr):+7.3f}")

print("\n=== MECHANISM 1d: control - is early-season error just a spread/total-level effect? ===")
# residualise |spread err| on |spread| decile, |total err| on total decile, then re-test
def resid_test(vals_key, ctrl_key, absfn):
    pts = [(g, absfn(g)) for g in G if g[ctrl_key] is not None]
    pts = [(g, v) for g, v in pts if v is not None]
    ctrl = sorted(set(round(abs(g[ctrl_key]), 1) for g, _ in pts))
    grp = collections.defaultdict(list)
    for g, v in pts:
        grp[round(abs(g[ctrl_key]), 1)].append(v)
    mu = {k: statistics.mean(v) for k, v in grp.items()}
    e = [v - mu[round(abs(g[ctrl_key]),1)] for g, v in pts if g["wk"] <= 3]
    r = [v - mu[round(abs(g[ctrl_key]),1)] for g, v in pts if g["wk"] > 3]
    print(f"  {vals_key:16s} residualised on {ctrl_key} level: wk1-3 mean={statistics.mean(e):+6.3f} (n={len(e)}) "
          f"rest={statistics.mean(r):+6.3f} (n={len(r)})  t={tstat_diff(e,r):+5.2f}")
resid_test("|spread err|", "spread", lambda g: abs(g["margin"] + g["spread"]))
resid_test("|total err|", "total", lambda g: abs(g["gtot"] - g["total"]))
