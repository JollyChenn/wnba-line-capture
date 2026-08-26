import csv, os, sys, math, collections, random, statistics
R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
H = os.path.join(R, "outputs", "hyp")


def load_master(require_recon=True):
    """team-game rows joined to closing game lines. Sorted by (season,date)."""
    gm = {}
    for r in csv.DictReader(open(os.path.join(R, "outputs", "gm", "gm_dataset.csv"), encoding="utf-8")):
        gm[r["game_id"]] = r
    der = collections.defaultdict(dict)
    for r in csv.DictReader(open(os.path.join(H, "pbp_derived.csv"), encoding="utf-8")):
        der[r["game_id"]][r["side"]] = r
    out = []
    for gid, sides in der.items():
        g = gm.get(gid)
        if not g or not g.get("total"):
            continue
        if require_recon and not all(int(s["recon_ok"]) for s in sides.values()):
            continue
        for sd in ("home", "away"):
            s = sides[sd]
            o = sides["away" if sd == "home" else "home"]
            team = g["home"] if sd == "home" else g["away"]
            opp = g["away"] if sd == "home" else g["home"]

            def fl(x):
                try:
                    return float(x)
                except Exception:
                    return None
            row = dict(game_id=gid, date=g["date"], season=int(g["season"]), team=team, opp=opp, side=sd,
                       pts=int(s["pts"]), opp_pts=int(o["pts"]),
                       tpm=int(s["tpm"]), tpa=int(s["tpa"]), fga=int(s["fga"]), fgm=int(s["fgm"]),
                       fta=int(s["fta"]), oreb=int(s["oreb"]), dreb=int(s["dreb"]),
                       opp_tpm=int(o["tpm"]), opp_tpa=int(o["tpa"]), opp_fga=int(o["fga"]),
                       opp_fgm=int(o["fgm"]), opp_oreb=int(o["oreb"]), opp_dreb=int(o["dreb"]),
                       opp_fta=int(o["fta"]),
                       total=fl(g["total"]), ou_o=fl(g["ou_o"]), ou_u=fl(g["ou_u"]),
                       spread=fl(g["spread"]), sp_h=fl(g["sp_h"]), sp_a=fl(g["sp_a"]),
                       game_total=int(g["home_score"]) + int(g["away_score"]),
                       margin=(int(g["home_score"]) - int(g["away_score"])) * (1 if sd == "home" else -1))
            row["sp_team"] = (row["spread"] if sd == "home"
                              else (-row["spread"] if row["spread"] is not None else None))
            row["sp_price"] = (row["sp_h"] if sd == "home" else row["sp_a"])
            row["tp_pct"] = (row["tpm"] / row["tpa"]) if row["tpa"] else None
            miss = row["fga"] - row["fgm"]
            row["oreb_pct"] = (row["oreb"] / (row["oreb"] + row["opp_dreb"])) if (row["oreb"] + row["opp_dreb"]) > 0 else None
            row["opp_oreb_pct"] = (row["opp_oreb"] / (row["opp_oreb"] + row["dreb"])) if (row["opp_oreb"] + row["dreb"]) > 0 else None
            row["poss"] = row["fga"] - row["oreb"] + 0.44 * row["fta"]
            row["opp_poss"] = row["opp_fga"] - row["opp_oreb"] + 0.44 * row["opp_fta"]
            out.append(row)
    out.sort(key=lambda r: (r["season"], r["date"], r["game_id"], r["side"]))
    return out


def series(rows):
    d = collections.defaultdict(list)
    for r in rows:
        d[(r["season"], r["team"])].append(r)
    for k, v in d.items():
        v.sort(key=lambda r: r["date"])
        for i, r in enumerate(v):
            r["idx"] = i
            r["tskey"] = k
    return d


def block_boot(units, n=4000, seed=1):
    """units: list of lists of per-bet profit grouped by independent unit."""
    rnd = random.Random(seed)
    flat = [p for u in units for p in u]
    if not flat:
        return (0.0, 0.0, 0.0)
    m = sum(flat) / len(flat)
    res = []
    N = len(units)
    for _ in range(n):
        s = 0.0
        c = 0
        for _ in range(N):
            u = units[rnd.randrange(N)]
            s += sum(u)
            c += len(u)
        if c:
            res.append(s / c)
    res.sort()
    return (m, res[int(0.025 * len(res))], res[int(0.975 * len(res))])


def ols(y, X):
    n = len(y)
    k = len(X[0]) + 1
    A = [[1.0] + list(x) for x in X]
    XtX = [[sum(A[i][a] * A[i][b] for i in range(n)) for b in range(k)] for a in range(k)]
    Xty = [sum(A[i][a] * y[i] for i in range(n)) for a in range(k)]
    M = [row[:] + [1.0 if i == j else 0.0 for j in range(k)] for i, row in enumerate(XtX)]
    for c in range(k):
        p = max(range(c, k), key=lambda r: abs(M[r][c]))
        if abs(M[p][c]) < 1e-12:
            return None
        M[c], M[p] = M[p], M[c]
        pv = M[c][c]
        M[c] = [v / pv for v in M[c]]
        for r in range(k):
            if r != c and M[r][c] != 0:
                f = M[r][c]
                M[r] = [a - f * b for a, b in zip(M[r], M[c])]
    inv = [row[k:] for row in M]
    beta = [sum(inv[a][b] * Xty[b] for b in range(k)) for a in range(k)]
    resid = [y[i] - sum(A[i][a] * beta[a] for a in range(k)) for i in range(n)]
    s2 = sum(e * e for e in resid) / max(n - k, 1)
    se = [math.sqrt(max(s2 * inv[a][a], 0)) for a in range(k)]
    t = [beta[a] / se[a] if se[a] > 0 else 0.0 for a in range(k)]
    return beta, se, t


def tstat(xs):
    if len(xs) < 3:
        return 0.0
    m = statistics.mean(xs)
    s = statistics.pstdev(xs)
    return m / (s / math.sqrt(len(xs))) if s > 0 else 0.0
