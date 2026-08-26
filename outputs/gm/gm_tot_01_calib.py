# STEP 1 - CALIBRATION of the closing total against the realised total.
import platform; platform._wmi = None
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from gm_tot_lib import load, priced_total, roi_side, summarise, fmt
import scipy.stats as st

df = priced_total(load())
print(f"priced-total rows: {len(df)}  seasons {df.season.min()}-{df.season.max()}")

y = df["game_total"].values.astype(float)
x = df["total"].values.astype(float)

# --- OLS realised ~ line
X = np.column_stack([np.ones(len(x)), x])
beta, *_ = np.linalg.lstsq(X, y, rcond=None)
resid = y - X@beta
s2 = resid@resid/(len(x)-2)
cov = s2*np.linalg.inv(X.T@X)
se = np.sqrt(np.diag(cov))
tcrit = st.t.ppf(0.975, len(x)-2)
print("\n=== 1a. realised_total = a + b*closing_total ===")
print(f"intercept a = {beta[0]:+8.3f}  SE {se[0]:.3f}  95%CI[{beta[0]-tcrit*se[0]:+.3f},{beta[0]+tcrit*se[0]:+.3f}]")
print(f"slope     b = {beta[1]:+8.4f}  SE {se[1]:.4f}  95%CI[{beta[1]-tcrit*se[1]:+.4f},{beta[1]+tcrit*se[1]:+.4f}]"
      f"   t(b=1) = {(beta[1]-1)/se[1]:+.2f}")
print(f"R2 = {1 - resid.var()/y.var():.4f}   resid sd = {resid.std():.2f} pts   line sd = {x.std():.2f}  realised sd = {y.std():.2f}")

# --- raw bias
d = y - x
print(f"\n=== 1b. raw bias (realised - line) ===")
tb = d.mean()/(d.std(ddof=1)/np.sqrt(len(d)))
print(f"mean {d.mean():+.3f} pts  sd {d.std():.2f}  t={tb:+.2f}  p={2*(1-st.norm.cdf(abs(tb))):.4f}")
print(f"over rate {100*(y>x).mean():.2f}%  pushes {(y==x).sum()}")
print(f"NOTE: breakeven over rate at the median price is ~52.67%. A {d.mean():+.2f} pt bias with sd {d.std():.1f}")
print(f"      moves the over rate by roughly {100*st.norm.cdf(d.mean()/d.std())-50:+.2f}pp.")

# --- by season
print("\n=== 1c. by season: bias, over rate, over ROI, under ROI ===")
print(f"{'ssn':>5} {'n':>5} {'meanline':>9} {'meantot':>8} {'bias':>7} {'t':>6} {'over%':>7} {'ovROI':>7} {'unROI':>7} {'slope':>7}")
for ssn, g in df.groupby("season"):
    yy, xx = g["game_total"].values.astype(float), g["total"].values.astype(float)
    dd = yy-xx
    tt = dd.mean()/(dd.std(ddof=1)/np.sqrt(len(dd)))
    po, lo_, wo = roi_side(g, True); pu, lu, wu = roi_side(g, False)
    so = summarise(po, lo_, wo, n_boot=1500, seed=1); su = summarise(pu, lu, wu, n_boot=1500, seed=1)
    A = np.column_stack([np.ones(len(xx)), xx]); b2,*_ = np.linalg.lstsq(A, yy, rcond=None)
    print(f"{ssn:>5} {len(g):>5} {xx.mean():9.2f} {yy.mean():8.2f} {dd.mean():+7.2f} {tt:+6.2f} "
          f"{100*(yy>xx).mean():7.2f} {so['roi']:+7.2f} {su['roi']:+7.2f} {b2[1]:7.3f}")

# --- 1d. does the market lag the scoring environment?
# Build a strictly-prior league scoring environment: trailing mean of realised totals over the
# previous K league games (chronological, excluding the current game). Compare with the line.
print("\n=== 1d. market lag vs league scoring environment (strictly prior info) ===")
df = df.sort_values(["date","game_id"]).reset_index(drop=True)
tot = df["game_total"].values.astype(float); line = df["total"].values.astype(float)
ssn = df["season"].values
for K in (20, 40, 60, 100):
    env = np.full(len(df), np.nan)
    for i in range(len(df)):
        # prior games in the SAME season only, else fall back to prior games overall
        j0 = max(0, i-K)
        prior = tot[j0:i]
        pssn = ssn[j0:i]
        m = pssn == ssn[i]
        if m.sum() >= 10:
            env[i] = prior[m].mean()
    ok = ~np.isnan(env)
    e, l, t = env[ok], line[ok], tot[ok]
    # does env - line predict the residual (t - l)?
    r = np.corrcoef(e-l, t-l)[0,1]
    n = ok.sum()
    tstat = r*np.sqrt(n-2)/np.sqrt(1-r*r)
    # also: does the line fully absorb env? regress line on env
    A = np.column_stack([np.ones(n), e]); b3,*_ = np.linalg.lstsq(A, l, rcond=None)
    print(f"  K={K:>3}  n={n:5d}  corr(env-line, realised-line) = {r:+.4f}  t={tstat:+.2f}"
          f"   line-on-env slope {b3[1]:+.3f}")
    # betting version: bet over when env-line > thresh
    sub = df[ok].copy(); gap = e - l
    for th in (2,4,6):
        for side,name in ((True,"OVER"),(False,"UNDER")):
            sel = (gap > th) if side else (gap < -th)
            if sel.sum() < 25: continue
            s2_ = summarise(*roi_side(sub[sel], side), n_boot=1500, seed=2)
            print("    " + fmt(f"K={K} env-gap {'>' if side else '<'}{'' if side else '-'}{th} bet {name}", s2_))

# --- lgenv feature: is it the same thing, and is it priced?
sub = df[df["lgenv"].notna()]
if len(sub) > 50:
    print(f"\n  lgenv available on n={len(sub)}: corr(lgenv, line)={np.corrcoef(sub.lgenv, sub.total)[0,1]:+.3f}"
          f"  corr(lgenv, realised)={np.corrcoef(sub.lgenv, sub.game_total)[0,1]:+.3f}"
          f"  corr(lgenv, realised-line)={np.corrcoef(sub.lgenv, sub.game_total-sub.total)[0,1]:+.3f}")
