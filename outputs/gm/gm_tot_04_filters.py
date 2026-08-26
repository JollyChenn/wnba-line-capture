# STEP 4 - FILTER GRID on blind over/under. Grid + ceiling declared and printed BEFORE results.
import platform; platform._wmi = None
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from gm_tot_lib import summarise, fmt

D = os.path.dirname(os.path.abspath(__file__))
df = pd.read_csv(os.path.join(D, "gm_tot_preds.csv"))
df = df[df.total.notna() & df.ou_o.notna() & df.ou_u.notna() & df.game_total.notna()].copy()
df["over_hit"] = (df.game_total > df.total).astype(int)
df["push"] = (df.game_total == df.total).astype(int)
df["absp"] = df.spread.abs()
df = df.reset_index(drop=True)
print(f"rows: {len(df)}  pushes: {df.push.sum()}")

def q(v, k):
    vv = v.dropna()
    return np.percentile(vv, np.linspace(0, 100, k+1))

# ---------- DECLARE THE FILTER GRID ----------
def build_buckets(d):
    B = {}
    e = q(d.total, 4)
    B["line"] = [(f"line<={e[1]:.0f}", d.total <= e[1]), (f"line {e[1]:.0f}-{e[2]:.0f}", (d.total > e[1]) & (d.total <= e[2])),
                 (f"line {e[2]:.0f}-{e[3]:.0f}", (d.total > e[2]) & (d.total <= e[3])), (f"line>{e[3]:.0f}", d.total > e[3])]
    e = q(d.absp, 4)
    B["spread"] = [(f"|sp|<={e[1]:.1f}", d.absp <= e[1]), (f"|sp| {e[1]:.1f}-{e[2]:.1f}", (d.absp > e[1]) & (d.absp <= e[2])),
                   (f"|sp| {e[2]:.1f}-{e[3]:.1f}", (d.absp > e[2]) & (d.absp <= e[3])), (f"|sp|>{e[3]:.1f}", d.absp > e[3])]
    B["b2b"] = [("no b2b", d.b2b_any == 0), ("one b2b", d.b2b_any == 1), ("both b2b", d.b2b_any == 2)]
    B["rest"] = [("both short rest<=2", (d.rest_h <= 2) & (d.rest_a <= 2)), ("both long rest>=3", (d.rest_h >= 3) & (d.rest_a >= 3))]
    B["season"] = [(f"ssn {s}", d.season == s) for s in sorted(d.season.unique())]
    ps = d.pace_s.dropna()
    if len(ps) > 100:
        e = np.percentile(ps, [0, 33.3, 66.7, 100])
        B["pace"] = [("pace low", d.pace_s <= e[1]), ("pace mid", (d.pace_s > e[1]) & (d.pace_s <= e[2])), ("pace high", d.pace_s > e[2])]
    lg = d.lgenv.dropna()
    if len(lg) > 100:
        e = np.percentile(lg, [0, 33.3, 66.7, 100])
        B["lgenv"] = [("lgenv low", d.lgenv <= e[1]), ("lgenv mid", (d.lgenv > e[1]) & (d.lgenv <= e[2])), ("lgenv high", d.lgenv > e[2])]
    e = q(d.exp_tot_raw, 3)
    B["scoremodel"] = [("expTot low", d.exp_tot_raw <= e[1]), ("expTot mid", (d.exp_tot_raw > e[1]) & (d.exp_tot_raw <= e[2])),
                       ("expTot high", d.exp_tot_raw > e[2])]
    return B

B = build_buckets(df)
MINN = 60
cellspec = []
for fam, lst in B.items():
    for lbl, m in lst:
        mm = np.asarray(m.fillna(False) if hasattr(m, "fillna") else m)
        if mm.sum() >= MINN:
            for side in (True, False):
                cellspec.append((fam, lbl, mm, side))
print("=== FILTER GRID DECLARED BEFORE RESULTS ===")
print(f"  families: {list(B)}   min n {MINN}   cells (bucket x side): {len(cellspec)}")

def roi_from(over_hit, oo, ou, push, over):
    win = over_hit == 1 if over else over_hit == 0
    odds = oo if over else ou
    live = push == 0
    pnl = np.where(win, odds-1.0, -1.0)
    return 100*pnl[live].mean(), int(live.sum()), 100*win[live].mean()

OH, OO, OU, PU, SS = df.over_hit.values, df.ou_o.values, df.ou_u.values, df.push.values, df.season.values
rng = np.random.default_rng(11)
NPERM = 1500
best = np.empty(NPERM)
for b in range(NPERM):
    oh, oo, ou, pu = OH.copy(), OO.copy(), OU.copy(), PU.copy()
    for s in np.unique(SS):                      # permute outcome+price jointly within season
        ix = np.where(SS == s)[0]; p = rng.permutation(ix)
        oh[ix], oo[ix], ou[ix], pu[ix] = OH[p], OO[p], OU[p], PU[p]
    mx = -99
    for fam, lbl, m, side in cellspec:
        r, n, _ = roi_from(oh[m], oo[m], ou[m], pu[m], side)
        if n >= MINN: mx = max(mx, r)
    best[b] = mx
p50, p95, p99 = np.percentile(best, [50, 95, 99])
print(f"  NOISE CEILING ({NPERM} within-season outcome permutations, best-of-grid ROI):")
print(f"    median {p50:+.2f}%   p95 {p95:+.2f}%   p99 {p99:+.2f}%")
print(f"  ==> a filter cell must beat {p95:+.2f}% ROI to count.\n")

print("=== 4. REAL filter results ===")
rows = []
for fam in B:
    print(f"\n-- family: {fam}")
    for lbl, m in B[fam]:
        mm = np.asarray(m.fillna(False) if hasattr(m, "fillna") else m)
        if mm.sum() < MINN: continue
        sub = df[mm]
        for side, nm in ((True, "OVER"), (False, "UNDER")):
            win = (sub.over_hit == 1) if side else (sub.over_hit == 0)
            odds = sub.ou_o if side else sub.ou_u
            live = sub.push.values == 0
            pnl = np.where(win, odds-1.0, -1.0)
            s = summarise(pnl, live, win.values, seed=4)
            flag = "  <-- ABOVE CEILING" if s["roi"] > p95 else ""
            print("  " + fmt(f"{lbl} | {nm}", s, flag))
            rows.append(dict(family=fam, bucket=lbl, side=nm, **s))
pd.DataFrame(rows).to_csv(os.path.join(D, "gm_tot_filters.csv"), index=False)
above = [r for r in rows if r["roi"] > p95]
print(f"\nceiling p95 = {p95:+.2f}%   cells above it: {len(above)} / {len(rows)}")
for r in above: print("   ", r)
