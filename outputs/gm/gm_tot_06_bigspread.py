# STEP 7 - FOLLOW-UP on the ONLY raw-points mechanism with |t|>3: big spreads go OVER.
# Declared follow-up tests: monotonicity, walk-forward by season, price shading, confounds.
import platform; platform._wmi = None
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from gm_tot_lib import summarise, fmt

D = os.path.dirname(os.path.abspath(__file__))
df = pd.read_csv(os.path.join(D, "gm_tot_preds.csv"))
df = df[df.total.notna() & df.ou_o.notna() & df.ou_u.notna() & df.game_total.notna() & df.spread.notna()].copy()
df["absp"] = df.spread.abs()
df["resid"] = df.game_total - df.total
df["over_hit"] = (df.game_total > df.total).astype(int)
df["absmargin"] = (df.home_score - df.away_score).abs()
print("n = %d" % len(df))


def cell(sub, over=True, seed=9):
    w = (sub.over_hit == 1) if over else (sub.over_hit == 0)
    od = sub.ou_o if over else sub.ou_u
    pnl = np.where(w, od - 1, -1)
    return summarise(pnl, np.ones(len(sub), bool), w.values, seed=seed)


print("\n=== 7a. MONOTONICITY of the raw bias in |spread| (finer bins) ===")
bins = [0, 2.5, 4.5, 6.5, 8.5, 11.5, 14.5, 99]
for lo, hi in zip(bins[:-1], bins[1:]):
    m = (df.absp > lo) & (df.absp <= hi)
    if m.sum() < 40:
        continue
    d = df.resid.values[m.values]
    t = d.mean() / (d.std(ddof=1) / np.sqrt(len(d)))
    s = cell(df[m])
    print("  |sp| %4.1f-%4.1f  n=%4d  bias %+6.2f pts t=%+5.2f  overrate %5.2f%%  overROI %+6.2f%% CI[%+.1f,%+.1f]"
          % (lo, hi, m.sum(), d.mean(), t, 100 * df.over_hit.values[m.values].mean(), s["roi"], s["lo"], s["hi"]))

print("\n=== 7b. WALK-FORWARD: rule '|spread| > 8.5 -> bet OVER', season by season ===")
print("  (threshold fixed at the full-sample upper quartile; report EVERY season)")
tot_pnl = 0.0; tot_n = 0
for s in sorted(df.season.unique()):
    g = df[(df.season == s) & (df.absp > 8.5)]
    if len(g) < 15:
        print("     ssn %s n=%d (too small)" % (s, len(g))); continue
    c = cell(g)
    d = g.resid.values
    print("     ssn %s  n=%4d  bias %+6.2f  hit %5.2f%%  ROI %+6.2f%%  CI[%+6.2f,%+6.2f]"
          % (s, c["n"], d.mean(), c["hit"], c["roi"], c["lo"], c["hi"]))
    tot_pnl += c["roi"] * c["n"] / 100.0; tot_n += c["n"]
print("     pooled  n=%d  ROI %+.2f%%" % (tot_n, 100 * tot_pnl / tot_n))
tr = df[(df.season <= 2022) & (df.absp > 8.5)]; te = df[(df.season >= 2023) & (df.absp > 8.5)]
ct, ce = cell(tr), cell(te)
print("  TRAIN 2019-2022: " + fmt("|sp|>8.5 OVER", ct))
print("  TEST  2023-2026: " + fmt("|sp|>8.5 OVER", ce))

print("\n=== 7c. IS IT IN THE PRICE? mean quoted over/under decimal odds by |spread| bucket ===")
for lo, hi in zip(bins[:-1], bins[1:]):
    m = (df.absp > lo) & (df.absp <= hi)
    if m.sum() < 40:
        continue
    g = df[m]
    ivo = 1 / g.ou_o; ivu = 1 / g.ou_u
    p_over = (ivo / (ivo + ivu)).mean()
    print("  |sp| %4.1f-%4.1f  n=%4d  mean ou_o %.3f  ou_u %.3f  de-vigged P(over)=%.4f  realised over %.4f"
          % (lo, hi, m.sum(), g.ou_o.mean(), g.ou_u.mean(), p_over, g.over_hit.mean()))
print("  If de-vigged P(over) is already tilted up in the big-spread bucket, the book has priced it.")

print("\n=== 7d. CONFOUND CHECK: is the big-spread over-bias just the 2026 season, or the line level? ===")
g = df[df.absp > 8.5]
print("  big-spread games by season: " + ", ".join("%s:%d" % (s, (g.season == s).sum()) for s in sorted(df.season.unique())))
print("  mean line big-spread %.2f vs rest %.2f" % (g.total.mean(), df[df.absp <= 8.5].total.mean()))
sub = df[df.season != 2026]
gg = sub[sub.absp > 8.5]
d = gg.resid.values; t = d.mean() / (d.std(ddof=1) / np.sqrt(len(d)))
c = cell(gg)
print("  EXCLUDING 2026: " + fmt("|sp|>8.5 OVER", c, "bias %+.2f t=%+.2f" % (d.mean(), t)))
# regression: resid ~ absp + season dummies
X = [np.ones(len(df)), df.absp.values]
for s in sorted(df.season.unique())[1:]:
    X.append((df.season.values == s).astype(float))
X = np.column_stack(X); y = df.resid.values
b, *_ = np.linalg.lstsq(X, y, rcond=None)
r = y - X @ b; s2 = r @ r / (len(y) - X.shape[1]); cov = s2 * np.linalg.inv(X.T @ X); se = np.sqrt(np.diag(cov))
print("  resid ~ |spread| + season FE:  beta(|spread|) = %+.4f pts per point of spread  t=%+.2f" % (b[1], b[1] / se[1]))

print("\n=== 7e. MECHANISM DETAIL: where do the extra points come from in blowouts? ===")
for lo, hi in ((0, 8.5), (8.5, 99)):
    m = (df.absp > lo) & (df.absp <= hi); g = df[m]
    print("  |sp| %4.1f-%4.1f  n=%4d  mean realised |margin| %5.2f (market %5.2f)  fav pts %6.2f  dog pts %6.2f"
          % (lo, hi, len(g), g.absmargin.mean(), g.absp.mean(),
             np.where(g.spread < 0, g.home_score, g.away_score).mean(),
             np.where(g.spread < 0, g.away_score, g.home_score).mean()))
# split the total residual into favourite-side and dog-side residual vs an implied split
g = df[df.absp > 8.5]
fav = np.where(g.spread < 0, g.home_score, g.away_score)
dog = np.where(g.spread < 0, g.away_score, g.home_score)
imp_fav = (g.total + g.absp) / 2; imp_dog = (g.total - g.absp) / 2
for nm, a, b2 in (("favourite", fav, imp_fav), ("underdog", dog, imp_dog)):
    d = a - b2.values; t = d.mean() / (d.std(ddof=1) / np.sqrt(len(d)))
    print("  big-spread %s scored %+.2f vs its implied %.2f  t=%+.2f" % (nm, d.mean(), b2.mean(), t))

print("\n=== 7f. does the market cover-rate confirm it? (spread market cross-check) ===")
g = df[df.absp > 8.5]
cov_fav = np.where(g.spread < 0, (g.home_score - g.away_score) > -g.spread, (g.away_score - g.home_score) > g.spread)
print("  favourite ATS cover rate in big-spread games: %.2f%% (n=%d)" % (100 * cov_fav.mean(), len(g)))
print("  If favourites cover AND totals go over, the extra points are the favourite's - a blowout")
print("  amplification, not a pace effect.")
