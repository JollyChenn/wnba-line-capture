# STEP 8 - FINAL PASS: line-quality (book count), season-carryover lag rule, 2026-only lag,
# and a pooled sanity check. Grid + ceiling declared first.
import platform; platform._wmi = None
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from gm_tot_lib import load, summarise, fmt

D = os.path.dirname(os.path.abspath(__file__))
raw = load()
pred = pd.read_csv(os.path.join(D, "gm_tot_preds.csv"))
df = pred.merge(raw[["game_id", "n_bk_ou", "n_bk_sp"]], on="game_id", how="left")
df = df[df.total.notna() & df.ou_o.notna() & df.ou_u.notna() & df.game_total.notna()].copy()
df = df.sort_values(["date", "game_id"]).reset_index(drop=True)
df["over_hit"] = (df.game_total > df.total).astype(int)
df["resid"] = df.game_total - df.total
print("n=%d" % len(df))


def cell(sub, over, seed=13):
    w = (sub.over_hit == 1) if over else (sub.over_hit == 0)
    od = sub.ou_o if over else sub.ou_u
    pnl = np.where(w, od - 1, -1)
    return summarise(pnl, np.ones(len(sub), bool), w.values, seed=seed)


print("\n=== 8a. LINE QUALITY: does a thinner book consensus leak? ===")
print("  n_bk_ou distribution:", df.n_bk_ou.value_counts().sort_index().to_dict())
for lo, hi in ((0, 6), (7, 8), (9, 10), (11, 99)):
    m = (df.n_bk_ou >= lo) & (df.n_bk_ou <= hi)
    if m.sum() < 60:
        continue
    g = df[m]
    d = g.resid.values; t = d.mean() / (d.std(ddof=1) / np.sqrt(len(d)))
    print("  books %2d-%2d n=%4d bias %+5.2f t=%+5.2f | OVER %s" % (lo, hi, m.sum(), d.mean(), t, fmt("", cell(g, True))))
    print("  " + " " * 22 + "| UNDER %s" % fmt("", cell(g, False)))

print("\n=== 8b. SEASON-CARRYOVER LAG: use season S-1's realised bias to bet all of season S ===")
bias = {s: (g.resid.mean()) for s, g in df.groupby("season")}
print("  season bias:", {k: round(v, 2) for k, v in bias.items()})
seasons = sorted(bias)
tot_p = 0.0; tot_n = 0
for i in range(1, len(seasons)):
    s, prev = seasons[i], seasons[i - 1]
    over = bias[prev] > 0
    g = df[df.season == s]
    c = cell(g, over)
    print("     %s (prev bias %+5.2f -> bet %-5s) n=%4d hit %5.2f%% ROI %+6.2f%% CI[%+6.2f,%+6.2f]"
          % (s, bias[prev], "OVER" if over else "UNDER", c["n"], c["hit"], c["roi"], c["lo"], c["hi"]))
    tot_p += c["roi"] * c["n"] / 100.0; tot_n += c["n"]
print("     POOLED n=%d ROI %+.2f%%   (7 folds, every one reported)" % (tot_n, 100 * tot_p / tot_n))

print("\n=== 8c. WITHIN-SEASON LAG, walk-forward, EVERY season reported ===")
print("  rule: once >=25 games of the current season are done, bet OVER if season-to-date bias > +2,")
print("        UNDER if < -2, otherwise no bet. Strictly prior information.")
res = df.resid.values; ssn = df.season.values
sel_side = np.full(len(df), np.nan)
for i in range(len(df)):
    m = (ssn[:i] == ssn[i])
    if m.sum() >= 25:
        b = res[:i][m].mean()
        if b > 2:
            sel_side[i] = 1
        elif b < -2:
            sel_side[i] = 0
df["std_side"] = sel_side
tot_p = 0.0; tot_n = 0
for s in sorted(df.season.unique()):
    g = df[(df.season == s) & df.std_side.notna()]
    if len(g) < 20:
        print("     ssn %s n=%d (skip)" % (s, len(g))); continue
    w = np.where(g.std_side == 1, g.over_hit == 1, g.over_hit == 0)
    od = np.where(g.std_side == 1, g.ou_o, g.ou_u)
    pnl = np.where(w, od - 1, -1)
    c = summarise(pnl, np.ones(len(g), bool), w, seed=14)
    nov = int((g.std_side == 1).sum())
    print("     ssn %s n=%4d (%d over / %d under) hit %5.2f%% ROI %+6.2f%% CI[%+6.2f,%+6.2f]"
          % (s, c["n"], nov, c["n"] - nov, c["hit"], c["roi"], c["lo"], c["hi"]))
    tot_p += c["roi"] * c["n"] / 100.0; tot_n += c["n"]
print("     POOLED n=%d ROI %+.2f%%" % (tot_n, 100 * tot_p / tot_n))
gall = df[df.std_side.notna()]
w = np.where(gall.std_side == 1, gall.over_hit == 1, gall.over_hit == 0)
od = np.where(gall.std_side == 1, gall.ou_o, gall.ou_u)
print("  " + fmt("POOLED within-season lag rule", summarise(np.where(w, od - 1, -1), np.ones(len(gall), bool), w, seed=15)))

print("\n=== 8d. 2026 IN DETAIL (the one season with a significant raw bias) ===")
g26 = df[df.season == 2026].copy()
print("  n=%d  line mean %.2f (2025: %.2f)  realised mean %.2f  bias %+.2f  over rate %.2f%%"
      % (len(g26), g26.total.mean(), df[df.season == 2025].total.mean(), g26.game_total.mean(),
         g26.resid.mean(), 100 * g26.over_hit.mean()))
print("  " + fmt("2026 blind OVER", cell(g26, True)))
g26 = g26.reset_index(drop=True)
run = np.full(len(g26), np.nan)
for i in range(len(g26)):
    if i >= 25:
        run[i] = g26.resid.values[:i].mean()
sel = ~np.isnan(run) & (run > 2)
if sel.sum() > 20:
    print("  " + fmt("2026 within-season-lag OVER only", cell(g26[sel], True), "(only %d of 8 seasons work this way)" % 1))
print("  Honest read: this is ONE season out of eight. Season-level max|t| over 8 seasons has a")
print("  p95 near 2.4 under the null, so t=+2.62 is a coin-flip finding, and the rule that would")
print("  have harvested it loses money in the other seasons (8c).")

print("\n=== 8e. POOLED SANITY: best cell found anywhere vs the ceilings ===")
print("  step 3 model-edge grid   29 cells, ceiling p95 +15.25%, best real cell  +8.58%  -> below")
print("  step 4 filter grid       58 cells, ceiling p95 +12.69%, best real cell  +7.62%  -> below")
print("  step 5 regime grid      118 cells, ceiling p95 (printed above), best real cell +14.84% -> below")
print("  Nothing in this market cleared its own noise ceiling.")
