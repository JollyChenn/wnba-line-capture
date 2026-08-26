# Shared helpers for the GAME TOTAL edge hunt. Read-only on the pipeline.
import platform; platform._wmi = None
import numpy as np, pandas as pd, os

D = os.path.dirname(os.path.abspath(__file__))
DS = os.path.join(D, "gm_dataset.csv")

FEATS = ["pstr","pnews","telo","zone","rest","b2b","form5","pace_d","pace_s","tov","oreb","ftr",
         "p3ar","p3pct","stk","bench","drop","fluid","pmr","pfr","ftp","blkr","q4","road",
         "m_scdef","m_pade","m_rb","m_vo","m_all5","lgenv"]

def load():
    df = pd.read_csv(DS)
    df = df.sort_values(["date","game_id"]).reset_index(drop=True)
    return df

def priced_total(df):
    """Rows with a usable total market + result."""
    m = df["total"].notna() & df["ou_o"].notna() & df["ou_u"].notna() & df["game_total"].notna()
    return df[m].copy()

def devig_pair(a, b):
    """Two decimal prices -> de-vigged probability of side A (normalise implied pair)."""
    ia, ib = 1.0/a, 1.0/b
    return ia/(ia+ib)

def roi_side(sub, over):
    """ROI of betting `over` (bool array or scalar) on rows in sub. Push -> stake returned (excluded)."""
    tot, line = sub["game_total"].values, sub["total"].values
    o_over, o_und = sub["ou_o"].values, sub["ou_u"].values
    over = np.asarray(over) if not np.isscalar(over) else np.full(len(sub), over, dtype=bool)
    push = tot == line
    win = np.where(over, tot > line, tot < line)
    odds = np.where(over, o_over, o_und)
    pnl = np.where(push, 0.0, np.where(win, odds-1.0, -1.0))
    live = ~push
    return pnl, live, win

def summarise(pnl, live, win, n_boot=4000, seed=0):
    pnl, live, win = np.asarray(pnl), np.asarray(live), np.asarray(win)
    n = int(live.sum())
    if n == 0:
        return dict(n=0, hit=float("nan"), roi=float("nan"), lo=float("nan"), hi=float("nan"))
    p = pnl[live]
    roi = 100.0*p.mean()
    hit = 100.0*win[live].mean()
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    boots = 100.0*p[idx].mean(axis=1)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return dict(n=n, hit=hit, roi=roi, lo=lo, hi=hi)

def fmt(lbl, s, extra=""):
    if s["n"] == 0:
        return f"{lbl:44s} n=0"
    return (f"{lbl:44s} n={s['n']:5d} hit={s['hit']:5.2f}% ROI={s['roi']:+6.2f}% "
            f"CI[{s['lo']:+6.2f},{s['hi']:+6.2f}] {extra}")
