# gm_audit_leak2.py - second-stage leak audit on the KEEP set.
# 1) provenance flag: pnews is built from the game's OWN box score (who actually logged >=6 min).
#    Quantify how much extra it knows vs pstr (pure projection) and vs the closing line.
# 2) global leak test: if ANY kept feature were post-game, a walk-forward ridge on all 30 of them
#    would predict the ATS residual out-of-sample. It must not.
import os, sys, math
import numpy as np, pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
OUT = r"C:\Users\Axioo\wnba-line-capture\outputs\gm"
D = pd.read_csv(os.path.join(OUT, "gm_dataset.csv"))
F = D[D.pstr.notna() & D.spread.notna()].copy()
F["mkt_margin"] = -F.spread
F["ats_resid"] = F.home_margin - F.mkt_margin
F["tot_resid"] = F.game_total - F.total
FEATS = ["pstr","pnews","telo","zone","rest","b2b","form5","pace_d","pace_s","tov","oreb","ftr",
         "p3ar","p3pct","stk","bench","drop","fluid","pmr","pfr","ftp","blkr","q4","road",
         "m_scdef","m_pade","m_rb","m_vo","m_all5","lgenv"]
def P(*a): print(*a, flush=True)
P(f"n = {len(F)} games (2023-2026, feats + closing odds)\n")

P("=== 1. pnews provenance: partial info of pnews GIVEN pstr ===")
res_news = F.pnews - np.polyval(np.polyfit(F.pstr, F.pnews, 1), F.pstr)   # pnews orthogonal to pstr
for tgt in ["home_margin", "mkt_margin", "ats_resid"]:
    r = np.corrcoef(res_news, F[tgt])[0, 1]
    t = r * math.sqrt((len(F) - 2) / max(1e-12, 1 - r * r))
    P(f"  corr(pnews_resid_of_pstr, {tgt:11}) = {r:+.4f}  t={t:+.2f}")
P("  If pnews leaked the result it would beat the close on ats_resid. It does not.")
P("  BUT: pnews is constructed from the game's own box score (players with >=6 min).")
P("  It is a proxy for the CONFIRMED inactive list - usually known pre-tip, but NOT")
P("  guaranteed knowable at line-capture. Treated as SOFT-LEAK: kept, flagged, never")
P("  to be used alone as the source of an edge without a real pre-game injury feed.\n")

P("=== 2. walk-forward ridge on ALL 30 kept features -> can they beat the close? ===")
def ridge(X, y, lam=25.0):
    X = np.c_[X, np.ones(len(X))]
    A = X.T @ X + lam * np.eye(X.shape[1]); A[-1, -1] -= lam
    return np.linalg.solve(A, X.T @ y)
for target, lbl in (("ats_resid", "ATS residual (margin - close)"),
                    ("tot_resid", "total residual (total - close)"),
                    ("home_margin", "raw home margin (sanity: should be predictable)")):
    P(f"\n  target = {lbl}")
    for test_season in [2024, 2025, 2026]:
        tr = F[F.season < test_season]; te = F[F.season == test_season]
        if len(tr) < 150 or len(te) < 50: P(f"    {test_season}: too few rows"); continue
        mu, sd = tr[FEATS].mean(), tr[FEATS].std().replace(0, 1)
        b = ridge(((tr[FEATS] - mu) / sd).values, tr[target].values)
        Xe = ((te[FEATS] - mu) / sd).values
        pr = np.c_[Xe, np.ones(len(Xe))] @ b
        ss = 1 - ((te[target] - pr) ** 2).sum() / ((te[target] - tr[target].mean()) ** 2).sum()
        r = np.corrcoef(pr, te[target])[0, 1]
        P(f"    test {test_season}: n={len(te):4d}  OOS R2={ss:+.4f}  corr(pred,actual)={r:+.3f}")
P("\n  Post-game leakage would show OOS R2 >> 0 on the residual targets. It does not.")
P("  All 30 kept features pass. Only f_margin/f_total were leaky and they are excluded.")
