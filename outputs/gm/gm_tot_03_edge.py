# STEP 3 - TotalEdge threshold curve, with the NOISE CEILING computed and printed FIRST.
import platform; platform._wmi = None
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from gm_tot_lib import roi_side, summarise, fmt

D = os.path.dirname(os.path.abspath(__file__))
df = pd.read_csv(os.path.join(D, "gm_tot_preds.csv"))
df = df[df.total.notna() & df.ou_o.notna() & df.ou_u.notna() & df.game_total.notna()].copy()

SIGNALS = {
    "score-model": ("model_total", None),      # edge = model_total - total
    "gbm-resid":   (None, "gbm_edge"),         # edge is already a residual forecast
    "ridge-resid": (None, "ridge_edge"),
}
THRESH = [2, 3, 4, 5, 7]
SIDES = ["follow", "over-only", "under-only"]

def edge_of(d, sig):
    mt, rc = SIGNALS[sig]
    if mt: return (d[mt] - d["total"]).values
    return d[rc].values

def cells(d, e, min_n=40):
    """yield (label, mask, over_bool_array)"""
    for th in THRESH:
        for side in SIDES:
            if side == "follow":
                m = np.abs(e) >= th; ov = e > 0
            elif side == "over-only":
                m = e >= th; ov = np.ones(len(e), bool)
            else:
                m = e <= -th; ov = np.zeros(len(e), bool)
            m = m & ~np.isnan(e)
            if m.sum() < min_n: continue
            yield f"{sig} |edge|>={th} {side}", m, ov[m]

# ---- DECLARE THE GRID AND COMPUTE THE CEILING BEFORE LOOKING AT ANY REAL RESULT ----
grids = {}
for sig in SIGNALS:
    d = df[~df[SIGNALS[sig][0] or SIGNALS[sig][1]].isna()].copy()
    if len(d) < 100: continue
    grids[sig] = d
ncells = 0
for sig, d in grids.items():
    ncells += sum(1 for _ in cells(d, edge_of(d, sig)))
print("=== GRID DECLARED BEFORE RESULTS ===")
print(f"  signals: {list(grids)}   thresholds {THRESH}   sides {SIDES}")
print(f"  total live cells (n>=40): {ncells}")

rng = np.random.default_rng(7)
NPERM = 1000
best = np.empty(NPERM)
for b in range(NPERM):
    mx = -99
    for sig, d in grids.items():
        e = edge_of(d, sig).copy()
        # permute the SIGNAL within season - preserves signal & outcome distributions, kills the link
        for s in d.season.unique():
            ix = np.where(d.season.values == s)[0]
            e[ix] = rng.permutation(e[ix])
        for lbl, m, ov in cells(d, e):
            sub = d[m]
            pnl, live, win = roi_side(sub, ov)
            if live.sum() >= 40:
                mx = max(mx, 100*pnl[live].mean())
    best[b] = mx
p50, p95, p99 = np.percentile(best, [50, 95, 99])
print(f"  NOISE CEILING ({NPERM} within-season signal permutations, best-of-grid ROI):")
print(f"    median {p50:+.2f}%   p95 {p95:+.2f}%   p99 {p99:+.2f}%")
print(f"  ==> a cell must beat {p95:+.2f}% ROI to count as anything at all.\n")

# ---- REAL RESULTS ----
print("=== 3. REAL threshold curve ===")
rows = []
for sig, d in grids.items():
    e = edge_of(d, sig)
    print(f"\n-- {sig}  (n available {len(d)}, edge sd {np.nanstd(e):.2f}, "
          f"corr with realised residual {np.corrcoef(e[~np.isnan(e)], (d.game_total-d.total).values[~np.isnan(e)])[0,1]:+.4f})")
    for lbl, m, ov in cells(d, e):
        sub = d[m]
        s = summarise(*roi_side(sub, ov), seed=3)
        flag = "  <-- ABOVE CEILING" if s["roi"] > p95 else ""
        print("  " + fmt(lbl, s, flag))
        rows.append(dict(cell=lbl, **s))
pd.DataFrame(rows).to_csv(os.path.join(D, "gm_tot_threshold_curve.csv"), index=False)
print(f"\nceiling p95 = {p95:+.2f}%   cells above it: {sum(1 for r in rows if r['roi']>p95)} / {len(rows)}")
