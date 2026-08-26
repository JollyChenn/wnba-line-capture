# STEP 2 - EXPECTED TOTAL MODEL, walk-forward by season. Pace x efficiency + direct fits.
# Everything strictly prior-information. Writes outputs/gm/gm_tot_preds.csv
import platform; platform._wmi = None
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from gm_tot_lib import load, FEATS

D = os.path.dirname(os.path.abspath(__file__))
df = load()
df = df[df["game_total"].notna()].copy().sort_values(["date","game_id"]).reset_index(drop=True)
print(f"all games with a result: {len(df)}")

# ---------- 2a. SCORE-DERIVED walk-forward team offence/defence (works on all 8 seasons) ----------
# Decayed team points-scored / points-allowed, carried across seasons with 0.6 shrink to league mean.
HL = 0.90            # per-game decay
teams = sorted(set(df.home) | set(df.away))
off = {t: None for t in teams}   # decayed pts scored
dfn = {t: None for t in teams}   # decayed pts allowed
lastd = {}
lg_run = []                       # rolling league mean team points

exp_tot, exp_off_sum, rest_h, rest_a, b2b_any, lgmean = [], [], [], [], [], []
gp_min = []
from datetime import date
def pdate(s):
    s = str(int(s)); return date(int(s[:4]), int(s[4:6]), int(s[6:8]))

cur_ssn = None
for i, r in df.iterrows():
    if r.season != cur_ssn:
        cur_ssn = r.season
        for t in teams:
            if off[t] is not None:
                m = np.mean(lg_run[-200:]) if lg_run else 81.0
                off[t] = m + 0.6*(off[t]-m); dfn[t] = m + 0.6*(dfn[t]-m)
        lastd.clear()
    h, a = r.home, r.away
    L = np.mean(lg_run[-200:]) if len(lg_run) >= 40 else 81.0
    oh = off[h] if off[h] is not None else L; dh = dfn[h] if dfn[h] is not None else L
    oa = off[a] if off[a] is not None else L; da = dfn[a] if dfn[a] is not None else L
    eh = oh + da - L; ea = oa + dh - L
    exp_tot.append(eh + ea); exp_off_sum.append(oh + oa); lgmean.append(L)
    rh = min((pdate(r.date)-pdate(lastd[h])).days, 6) if h in lastd else 3
    ra = min((pdate(r.date)-pdate(lastd[a])).days, 6) if a in lastd else 3
    rest_h.append(rh); rest_a.append(ra); b2b_any.append(int(rh <= 1) + int(ra <= 1))
    gp_min.append(min(sum(1 for _ in [1] if off[h] is not None), 1) + min(sum(1 for _ in [1] if off[a] is not None), 1))
    # update AFTER
    hs, as_ = float(r.home_score), float(r.away_score)
    for t, sc, al in ((h, hs, as_), (a, as_, hs)):
        off[t] = sc if off[t] is None else HL*off[t] + (1-HL)*sc
        dfn[t] = al if dfn[t] is None else HL*dfn[t] + (1-HL)*al
    lg_run += [hs, as_]
    lastd[h] = r.date; lastd[a] = r.date

df["exp_tot_raw"] = exp_tot
df["off_sum"] = exp_off_sum
df["lg_run"] = lgmean
df["rest_h"] = rest_h; df["rest_a"] = rest_a; df["b2b_any"] = b2b_any
df["warm"] = gp_min

# drop first 60 games of the very first season (cold start)
df = df.iloc[60:].reset_index(drop=True)

# ---------- 2b. walk-forward calibrated model ----------
# For each test season, fit realised_total ~ exp_tot_raw + b2b_any (+ lg_run) on ALL PRIOR seasons.
seasons = sorted(df.season.unique())
df["model_total"] = np.nan
COLS = ["exp_tot_raw", "b2b_any", "lg_run"]
for s in seasons[2:]:
    tr = df[df.season < s]; te = df.season == s
    if len(tr) < 200: continue
    X = np.column_stack([np.ones(len(tr))] + [tr[c].values for c in COLS])
    y = tr["game_total"].values.astype(float)
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    Xt = np.column_stack([np.ones(te.sum())] + [df.loc[te, c].values for c in COLS])
    df.loc[te, "model_total"] = Xt @ b

# ---------- 2c. RMSE model vs market ----------
print("\n=== 2c. RMSE: score-based walk-forward model vs the 10-book closing total ===")
print(f"{'ssn':>5} {'n':>5} {'RMSE_model':>11} {'RMSE_market':>12} {'RMSE_blend':>11} {'corr(m,mkt)':>12}")
sub = df[df.model_total.notna() & df.total.notna()]
for s, g in sub.groupby("season"):
    rm = np.sqrt(((g.model_total-g.game_total)**2).mean())
    rk = np.sqrt(((g.total-g.game_total)**2).mean())
    bl = np.sqrt((((0.5*g.model_total+0.5*g.total)-g.game_total)**2).mean())
    print(f"{s:>5} {len(g):>5} {rm:11.2f} {rk:12.2f} {bl:11.2f} {np.corrcoef(g.model_total,g.total)[0,1]:12.3f}")
rm = np.sqrt(((sub.model_total-sub.game_total)**2).mean()); rk = np.sqrt(((sub.total-sub.game_total)**2).mean())
print(f"{'ALL':>5} {len(sub):>5} {rm:11.2f} {rk:12.2f} "
      f"{np.sqrt((((0.5*sub.model_total+0.5*sub.total)-sub.game_total)**2).mean()):11.2f}")

# does the model add ANYTHING to the market? regress realised on (market, model)
X = np.column_stack([np.ones(len(sub)), sub.total.values, sub.model_total.values])
y = sub.game_total.values.astype(float)
b, *_ = np.linalg.lstsq(X, y, rcond=None)
res = y - X@b; s2 = res@res/(len(y)-3); cov = s2*np.linalg.inv(X.T@X); se = np.sqrt(np.diag(cov))
print(f"\n  encompassing regression realised = a + b1*market + b2*model")
print(f"   b1(market) = {b[1]:+.3f} (t={b[1]/se[1]:+.2f})   b2(model) = {b[2]:+.3f} (t={b[2]/se[2]:+.2f})")
print("   b2 indistinguishable from 0 => the model adds nothing the close does not already have.")

# ---------- 2d. GBM on the RESIDUAL, 2023-2026 feats, walk-forward ----------
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import RidgeCV
fs = df[df.pace_s.notna() & df.total.notna()].copy()
fs["resid"] = fs.game_total - fs.total
use = [c for c in FEATS if c in fs.columns] + ["exp_tot_raw", "off_sum", "lg_run", "b2b_any"]
print(f"\n=== 2d. residual models on feats_v5 span, n={len(fs)} ===")
print(f"{'test ssn':>9} {'n':>5} {'GBM R2':>8} {'Ridge R2':>9} {'GBM RMSE':>9} {'null RMSE':>10}")
fs["gbm_edge"] = np.nan; fs["ridge_edge"] = np.nan
for s in sorted(fs.season.unique())[1:]:
    tr = fs[fs.season < s]; te = fs.season == s
    if len(tr) < 150: continue
    Xtr = tr[use].fillna(0).values; ytr = tr["resid"].values
    Xte = fs.loc[te, use].fillna(0).values; yte = fs.loc[te, "resid"].values
    g = HistGradientBoostingRegressor(max_depth=3, max_iter=200, learning_rate=0.05,
                                      min_samples_leaf=30, random_state=0).fit(Xtr, ytr)
    pg = g.predict(Xte)
    rr = RidgeCV(alphas=np.logspace(0, 4, 20)).fit((Xtr-Xtr.mean(0))/(Xtr.std(0)+1e-9), ytr)
    pr = rr.predict((Xte-Xtr.mean(0))/(Xtr.std(0)+1e-9))
    fs.loc[te, "gbm_edge"] = pg; fs.loc[te, "ridge_edge"] = pr
    r2g = 1 - ((yte-pg)**2).sum()/((yte-yte.mean())**2).sum()
    r2r = 1 - ((yte-pr)**2).sum()/((yte-yte.mean())**2).sum()
    print(f"{s:>9} {te.sum():>5} {r2g:8.4f} {r2r:9.4f} {np.sqrt(((yte-pg)**2).mean()):9.2f} {yte.std():10.2f}")

out = df[["game_id","date","season","home","away","home_score","away_score","total","ou_o","ou_u",
          "game_total","spread","ml_h","ml_a","model_total","exp_tot_raw","off_sum","lg_run",
          "rest_h","rest_a","b2b_any","pace_s","pace_d","lgenv","p3ar","p3pct","tov","oreb","ftr"]].copy()
out = out.merge(fs[["game_id","gbm_edge","ridge_edge"]], on="game_id", how="left")
out.to_csv(os.path.join(D, "gm_tot_preds.csv"), index=False)
print(f"\nwrote gm_tot_preds.csv  rows={len(out)}")
