# brute_v3.py - proper brute-force over feature combos for the MARGIN model.
# Protocol: fit OLS (ridge 1e-3) on 2023-24 ONLY, evaluate MAE + side-acc on 2025-26 ONLY.
# All subsets size 1-4 of the 17 features. Multiplicity guard: ~3.2k combos; report top-10 and
# whether the best beats the single-feature champion by more than noise (~0.15 MAE at n=490).
import csv, os, itertools, statistics, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
rows = list(csv.DictReader(open(os.path.join(D, "feats_v3.csv"), encoding="utf-8")))
FEATS = ["pstr","pnews","telo","zone","rest","b2b","form5","pace_d","pace_s","tov","oreb","ftr",
         "p3ar","p3pct","stk","bench","drop"]
tr = [r for r in rows if r["season"] in ("2023","2024")]
te = [r for r in rows if r["season"] in ("2025","2026")]
def X(rs, fs): return [[float(r[f_]) for f_ in fs] + [1.0] for r in rs]
def Y(rs): return [float(r["margin"]) for r in rs]
def solve(A, b):                                       # gaussian elimination
    n = len(A)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        p = max(range(c, n), key=lambda r_: abs(M[r_][c]))
        M[c], M[p] = M[p], M[c]
        if abs(M[c][c]) < 1e-12: return None
        M[c] = [v / M[c][c] for v in M[c]]
        for r_ in range(n):
            if r_ != c and M[r_][c]:
                M[r_] = [a - M[r_][c] * b2 for a, b2 in zip(M[r_], M[c])]
    return [M[i][n] for i in range(n)]
def fit_eval(fs):
    Xt, yt = X(tr, fs), Y(tr)
    k = len(fs) + 1
    XtX = [[sum(Xt[i][a] * Xt[i][b_] for i in range(len(Xt))) + (1e-3 if a == b_ else 0)
            for b_ in range(k)] for a in range(k)]
    Xty = [sum(Xt[i][a] * yt[i] for i in range(len(Xt))) for a in range(k)]
    beta = solve(XtX, Xty)
    if not beta: return None
    Xe, ye = X(te, fs), Y(te)
    pred = [sum(b_ * x_ for b_, x_ in zip(beta, xr)) for xr in Xe]
    mae = statistics.mean(abs(p - y) for p, y in zip(pred, ye))
    acc = statistics.mean((p > 0) == (y > 0) for p, y in zip(pred, ye))
    return mae, acc, beta
print(f"train {len(tr)} test {len(te)}\n--- single features ---")
singles = []
for f_ in FEATS:
    r_ = fit_eval([f_])
    if r_: singles.append((r_[0], r_[1], f_))
for m, a, f_ in sorted(singles)[:8]: print(f"  {f_:8} MAE={m:.2f} acc={a:.1%}")
best1 = min(singles)[0]
print("--- brute-force combos (size 2-4) ---")
results = []
for k in (2, 3, 4):
    for fs in itertools.combinations(FEATS, k):
        r_ = fit_eval(list(fs))
        if r_: results.append((r_[0], r_[1], fs))
results.sort()
for m, a, fs in results[:10]: print(f"  MAE={m:.2f} acc={a:.1%}  {'+'.join(fs)}")
m, a, fs = results[0]
print(f"\nbest combo vs best single: {m:.2f} vs {best1:.2f} (need <{best1-0.15:.2f} to beat noise+multiplicity)")
# ---- TOTALS quick pass (same protocol, target=total) ----
def Yt(rs): return [float(r["total"]) for r in rs]
def fit_eval_t(fs):
    Xt, yt = X(tr, fs), Yt(tr)
    k = len(fs) + 1
    XtX = [[sum(Xt[i][a]*Xt[i][b_] for i in range(len(Xt))) + (1e-3 if a==b_ else 0) for b_ in range(k)] for a in range(k)]
    Xty = [sum(Xt[i][a]*yt[i] for i in range(len(Xt))) for a in range(k)]
    beta = solve(XtX, Xty)
    if not beta: return None
    Xe, ye = X(te, fs), Yt(te)
    pred = [sum(b_*x_ for b_,x_ in zip(beta,xr)) for xr in Xe]
    return statistics.mean(abs(p-y) for p,y in zip(pred,ye))
base_t = statistics.mean(abs(statistics.mean(Yt(tr)) - y) for y in Yt(te))
tres = sorted((fit_eval_t(list(fs)), fs) for k in (1,2,3) for fs in itertools.combinations(FEATS,k) if fit_eval_t(list(fs)))
print(f"\nTOTALS: constant-baseline MAE={base_t:.2f}; top-3 combos:")
for m, fs in tres[:3]: print(f"  MAE={m:.2f}  {'+'.join(fs)}")
