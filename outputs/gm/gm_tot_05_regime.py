# STEP 5 - SEASONAL REGIME / MEAN-REVERSION: does a run of unders predict the next under?
# STEP 6 - MECHANISM in raw points.
import platform; platform._wmi = None
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from gm_tot_lib import summarise, fmt
from collections import defaultdict

D = os.path.dirname(os.path.abspath(__file__))
df = pd.read_csv(os.path.join(D, "gm_tot_preds.csv"))
df = df[df.total.notna() & df.ou_o.notna() & df.ou_u.notna() & df.game_total.notna()].copy()
df = df.sort_values(["date", "game_id"]).reset_index(drop=True)
df["over_hit"] = (df.game_total > df.total).astype(int)
df["resid"] = df.game_total - df.total
N = len(df)

oh, res, ssn = df.over_hit.values, df.resid.values, df.season.values
home, away = df.home.values, df.away.values

sig = {}
for k in (3, 5, 8, 12):
    v = np.full(N, np.nan)
    for i in range(N):
        j0 = i - 1
        pick = []
        while j0 >= 0 and len(pick) < k and ssn[j0] == ssn[i]:
            pick.append(j0); j0 -= 1
        if len(pick) == k:
            v[i] = np.mean(oh[pick])
    sig["lg_over_rate_%d" % k] = v
for K in (20, 40, 60):
    v = np.full(N, np.nan)
    for i in range(N):
        j0 = max(0, i - K); pr = res[j0:i]; ps = ssn[j0:i]
        m = ps == ssn[i]
        if m.sum() >= max(10, K // 2):
            v[i] = pr[m].mean()
    sig["lg_resid_mean_%d" % K] = v

for k in (3, 5):
    v = np.full(N, np.nan); hist = defaultdict(list); cur = None
    for i in range(N):
        if ssn[i] != cur:
            cur = ssn[i]; hist = defaultdict(list)
        a, b = hist[home[i]], hist[away[i]]
        if len(a) >= k and len(b) >= k:
            v[i] = (np.mean(a[-k:]) + np.mean(b[-k:])) / 2
        hist[home[i]].append(oh[i]); hist[away[i]].append(oh[i])
    sig["tm_over_rate_%d" % k] = v
for k in (3, 5):
    v = np.full(N, np.nan); hist = defaultdict(list); cur = None
    for i in range(N):
        if ssn[i] != cur:
            cur = ssn[i]; hist = defaultdict(list)
        a, b = hist[home[i]], hist[away[i]]
        if len(a) >= k and len(b) >= k:
            v[i] = (np.mean(a[-k:]) + np.mean(b[-k:])) / 2
        hist[home[i]].append(res[i]); hist[away[i]].append(res[i])
    sig["tm_resid_%d" % k] = v
for kk, vv in sig.items():
    df[kk] = vv

RATE_SIGS = [k for k in sig if "over_rate" in k]
RES_SIGS = [k for k in sig if "resid" in k]
RATE_TH = [0.60, 0.70, 0.80]
RES_TH = [1.5, 3.0, 5.0]
MINN = 60


def gridcells(d):
    out = []
    for s in RATE_SIGS:
        v = d[s].values
        for th in RATE_TH:
            for hi in (True, False):
                for follow in (True, False):
                    m = (v >= th) if hi else (v <= 1 - th)
                    m = m & ~np.isnan(v)
                    over = hi if follow else (not hi)
                    lbl = "%s %s%.2f %s -> %s" % (s, ">=" if hi else "<=", th if hi else 1 - th,
                                                  "FOLLOW" if follow else "FADE", "OVER" if over else "UNDER")
                    out.append((lbl, m, over))
    for s in RES_SIGS:
        v = d[s].values
        for th in RES_TH:
            for hi in (True, False):
                for follow in (True, False):
                    m = (v >= th) if hi else (v <= -th)
                    m = m & ~np.isnan(v)
                    over = hi if follow else (not hi)
                    lbl = "%s %s%.1f %s -> %s" % (s, ">=+" if hi else "<=-", th,
                                                  "FOLLOW" if follow else "FADE", "OVER" if over else "UNDER")
                    out.append((lbl, m, over))
    return [(l, m, o) for l, m, o in out if m.sum() >= MINN]


cs = gridcells(df)
print("=== REGIME GRID DECLARED BEFORE RESULTS ===")
print("  streak signals %s at %s" % (RATE_SIGS, RATE_TH))
print("  residual signals %s at %s" % (RES_SIGS, RES_TH))
print("  x FOLLOW/FADE x high/low.  live cells (n>=%d): %d" % (MINN, len(cs)))

OH, OO, OU = df.over_hit.values, df.ou_o.values, df.ou_u.values
rng = np.random.default_rng(23)
NPERM = 1200
best = np.empty(NPERM)
masks = [(m, o) for _, m, o in cs]
for b in range(NPERM):
    oh2, oo2, ou2 = OH.copy(), OO.copy(), OU.copy()
    for s in np.unique(ssn):
        ix = np.where(ssn == s)[0]; p = rng.permutation(ix)
        oh2[ix], oo2[ix], ou2[ix] = OH[p], OO[p], OU[p]
    mx = -99.0
    for m, o in masks:
        w = (oh2[m] == 1) if o else (oh2[m] == 0)
        od = oo2[m] if o else ou2[m]
        mx = max(mx, 100 * np.where(w, od - 1, -1).mean())
    best[b] = mx
p95 = np.percentile(best, 95)
print("  NOISE CEILING: median %+.2f%%  p95 %+.2f%%  p99 %+.2f%%"
      % (np.percentile(best, 50), p95, np.percentile(best, 99)))
print("  ==> must beat %+.2f%% ROI.\n" % p95)

print("=== 5. REAL regime / mean-reversion results ===")
rows = []
for lbl, m, o in cs:
    sub = df[m]
    w = (sub.over_hit == 1) if o else (sub.over_hit == 0)
    od = sub.ou_o if o else sub.ou_u
    pnl = np.where(w, od - 1, -1); live = np.ones(len(sub), bool)
    s = summarise(pnl, live, w.values, seed=5)
    flag = "  <-- ABOVE CEILING" if s["roi"] > p95 else ""
    print("  " + fmt(lbl, s, flag)); rows.append(dict(cell=lbl, **s))
pd.DataFrame(rows).to_csv(os.path.join(D, "gm_tot_regime.csv"), index=False)
print("\ncells above ceiling: %d / %d" % (sum(1 for r in rows if r["roi"] > p95), len(rows)))

print("\n=== 5b. MECHANISM in raw points: does a prior run predict the NEXT residual? ===")
for s in RATE_SIGS + RES_SIGS:
    v = df[s].values; ok = ~np.isnan(v)
    r = np.corrcoef(v[ok], res[ok])[0, 1]; n = int(ok.sum())
    t = r * np.sqrt(n - 2) / np.sqrt(1 - r * r)
    print("  corr(%18s, next realised-line) = %+.4f  t=%+.2f  n=%d" % (s, r, t, n))
print("  (positive = momentum/market lags; negative = mean reversion; |t|<2.9 is inside a 10-test ceiling)")

print("\n=== 6. MECHANISM: mean realised-minus-line by bucket (raw points, no prices) ===")
df["absp"] = df.spread.abs()


def show(name, groups):
    print("  -- " + name)
    for lbl, m in groups:
        mm = np.asarray(m.fillna(False) if hasattr(m, "fillna") else m)
        if mm.sum() < 50:
            continue
        d = res[mm]
        t = d.mean() / (d.std(ddof=1) / np.sqrt(len(d)))
        print("     %-22s n=%5d  mean(realised-line) = %+6.2f pts  t=%+5.2f  realised %6.2f vs line %6.2f"
              % (lbl, mm.sum(), d.mean(), t, df.game_total.values[mm].mean(), df.total.values[mm].mean()))


e = np.percentile(df.absp.dropna(), [0, 25, 50, 75, 100])
show("|spread| quartiles", [("|sp|<=%.1f" % e[1], df.absp <= e[1]),
                            ("|sp| %.1f-%.1f" % (e[1], e[2]), (df.absp > e[1]) & (df.absp <= e[2])),
                            ("|sp| %.1f-%.1f" % (e[2], e[3]), (df.absp > e[2]) & (df.absp <= e[3])),
                            ("|sp|>%.1f" % e[3], df.absp > e[3])])
lg = df.lgenv.dropna(); e = np.percentile(lg, [0, 33.3, 66.7, 100])
show("lgenv terciles", [("lgenv low", df.lgenv <= e[1]),
                        ("lgenv mid", (df.lgenv > e[1]) & (df.lgenv <= e[2])),
                        ("lgenv high", df.lgenv > e[2])])
show("season", [("ssn %s" % s, df.season == s) for s in sorted(df.season.unique())])

d26 = df[df.season == 2026].copy(); d26["mo"] = (d26.date // 100) % 100
print("  -- 2026 by month")
for mo, g in d26.groupby("mo"):
    d = (g.game_total - g.total).values
    if len(d) < 12:
        continue
    t = d.mean() / (d.std(ddof=1) / np.sqrt(len(d)))
    print("     2026-%02d  n=%4d  mean(realised-line) = %+6.2f  t=%+5.2f  over rate %5.1f%%"
          % (mo, len(g), d.mean(), t, 100 * (g.game_total > g.total).mean()))
