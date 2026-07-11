# calibrate.py - Phase 3+4: minutes projection + aggregation -> game predictions, walk-forward.
# Fit margin scale + home adv on 2023-24; TEST on 2025-26. Compare vs dumb TEAM-Elo baseline (G3 gate:
# player model must beat baseline MAE/Brier or the complexity is unearned).
# Minutes model: exp-decay (half-life 5 games) of recent minutes; roster = players in team's last 3 games;
# normalized to 200 team-minutes. Ratings: same engine as engine.py, re-run inline pregame (walk-forward).
import csv, os, statistics, math, sys
from collections import defaultdict, deque
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
games = sorted(csv.DictReader(open(os.path.join(D, "games_full.csv"), encoding="utf-8")),
               key=lambda g: (g["date"], g["game_id"]))
box = defaultdict(list)
for r in csv.DictReader(open(os.path.join(D, "box_full.csv"), encoding="utf-8")):
    box[r["game_id"]].append(r)
def f(x):
    try: return float(x)
    except Exception: return 0.0
LGTS, C_M, C_SD, PPP_M, PPP_SD = 0.542, 4.80, 6.03, 101.9, 13.5   # from engine.py pass 0
def comp36(r):
    m = f(r["min"])
    if m < 6: return None
    return ((f(r["pts"]) - LGTS * 2 * (f(r["fga"]) + 0.44 * f(r["fta"])))
            + 0.7 * f(r["ast"]) - f(r["to"]) + 0.7 * f(r["oreb"]) + 0.3 * f(r["dreb"])
            + 0.15 * (f(r["fga"]) + 0.44 * f(r["fta"]))) * 36 / m

oR, dR, gp = defaultdict(float), defaultdict(float), defaultdict(int)
recmin = defaultdict(lambda: deque(maxlen=10))        # per player recent minutes
roster = defaultdict(lambda: deque(maxlen=3))         # per team: sets of aids from last 3 games
telo = defaultdict(lambda: 1500.0)                    # baseline team Elo
def lr(g): return 0.28 * 15 / (15 + g) + 0.04
CLIP = 2.5
season_cur = None
rows_fit, rows_test = [], []                          # (pstrength_diff, elodiff, margin, home_win)

def proj_minutes(team):
    seen = {}
    for s in roster[team]:
        for a in s: seen[a] = 1
    pm = {}
    for a in seen:
        ms = list(recmin[a])
        if not ms: continue
        wts = [0.87 ** (len(ms) - 1 - i) for i in range(len(ms))]
        pm[a] = sum(m * w for m, w in zip(ms, wts)) / sum(wts)
    tot = sum(pm.values())
    if tot < 100: return None
    return {a: m * 200 / tot for a, m in pm.items()}

def strength(team):
    pm = proj_minutes(team)
    if not pm: return None
    o = sum(oR[a] * m for a, m in pm.items()) / 200
    d = sum(dR[a] * m for a, m in pm.items()) / 200
    return o + d                                       # net team quality in z-units

for g in games:
    if g["season"] != season_cur:
        season_cur = g["season"]
        for k in list(oR): oR[k] *= 0.7
        for k in list(dR): dR[k] *= 0.7
        for k in list(telo): telo[k] = 1500 + 0.7 * (telo[k] - 1500)
    rows = box.get(g["game_id"], [])
    T = defaultdict(list)
    for r in rows: T[r["team"]].append(r)
    if len(T) != 2 or not g["home_score"]: continue
    home, away = g["home"], g["away"]
    if home not in T or away not in T: continue
    margin = f(g["home_score"]) - f(g["away_score"])
    # ---- PREGAME prediction (uses only past data) ----
    sh, sa = strength(home), strength(away)
    if sh is not None and sa is not None:
        shock = 0                                   # a projected top-5-minutes player did NOT actually play
        for tmx in (home, away):
            pmx = proj_minutes(tmx) or {}
            top5 = sorted(pmx, key=lambda a: -pmx[a])[:5]
            played = {r["aid"] for r in T[tmx] if f(r["min"]) >= 6}
            if any(a not in played for a in top5): shock = 1
        def strength_avail(tmx):                # projection EXCLUDING players who didn't suit up (= injury news)
            pmx = proj_minutes(tmx) or {}
            played = {r["aid"] for r in T[tmx] if f(r["min"]) >= 6}
            pmx = {a: m for a, m in pmx.items() if a in played}
            tot = sum(pmx.values()) or 1
            return sum((oR[a] + dR[a]) * m for a, m in pmx.items()) / tot
        rec = (sh - sa, telo[home] - telo[away], margin, 1 if margin > 0 else 0, shock,
               strength_avail(home) - strength_avail(away))
        (rows_fit if g["season"] in ("2023", "2024") else rows_test).append(rec)
    # ---- update baseline team Elo (538-style MOV) ----
    ed = telo[home] + 80 - telo[away]
    eh = 1 / (1 + 10 ** (-ed / 400))
    mov = (abs(margin) + 3) ** 0.8 / (7.5 + 0.006 * abs(ed))
    delta = 20 * mov * ((1 if margin > 0 else 0) - eh)
    telo[home] += delta; telo[away] -= delta
    # ---- update player ratings (same as engine.py) ----
    (tA, ra), (tB, rb) = T.items()
    def agg(rr, R):
        tm_ = sum(f(r["min"]) for r in rr) or 1
        return sum(R[r["aid"]] * f(r["min"]) for r in rr) / tm_
    dAgg = {tA: agg(ra, dR), tB: agg(rb, dR)}
    oAgg = {tA: agg(ra, oR), tB: agg(rb, oR)}
    for tm, rr, opp in ((tA, ra, tB), (tB, rb, tA)):
        for r in rr:
            c = comp36(r)
            if c is None: continue
            aid = r["aid"]
            act = max(-CLIP, min(CLIP, (c - C_M) / C_SD))
            oR[aid] += lr(gp[aid]) * min(f(r["min"]) / 30, 1) * (act - (oR[aid] - dAgg[opp]))
        poss = sum(f(x["fga"]) + 0.44 * f(x["fta"]) + f(x["to"]) - f(x["oreb"]) for x in rows if x["team"] == opp)
        opts = sum(f(x["pts"]) for x in rows if x["team"] == opp)
        if poss > 40:
            dz = max(-CLIP, min(CLIP, ((PPP_M + oAgg[opp] * 3 - dAgg[tm] * 3) - 100 * opts / poss) / PPP_SD))
            for r in rr:
                m = f(r["min"])
                if m < 6: continue
                stz = ((f(r["stl"]) + f(r["blk"])) * 36 / m - 1.5) / 1.5
                dR[r["aid"]] += lr(gp[r["aid"]]) * (m / 200) * (dz - dR[r["aid"]]) + 0.01 * max(-2, min(2, stz))
        for r in rr:
            if f(r["min"]) >= 6:
                gp[r["aid"]] += 1; recmin[r["aid"]].append(f(r["min"]))
        roster[tm].append({r["aid"] for r in rr if f(r["min"]) >= 6})

# ---- fit on 23-24, evaluate on 25-26 ----
def ols(xs, ys):                                       # y = a*x + b
    n = len(xs); mx, my = sum(xs) / n, sum(ys) / n
    a = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sum((x - mx) ** 2 for x in xs) or 1)
    return a, my - a * mx
def logistic_fit(xs, ys, it=300):             # p = sigmoid(a*x+b); tiny eta + small init for Elo-scale x
    big = max(abs(x) for x in xs) > 50
    eta = 1e-5 if big else 0.1
    a, b = (0.005 if big else 0.1), 0.0
    for _ in range(it):
        ga = gb = 0
        for x, y in zip(xs, ys):
            p = 1 / (1 + math.exp(-max(-30, min(30, a * x + b)))); ga += (p - y) * x; gb += (p - y)
        a -= eta * ga / len(xs); b -= eta * gb / len(xs)
    return a, b
print(f"fit games: {len(rows_fit)}, test games: {len(rows_test)}")
for label, xi in (("PLAYER-model", 0), ("PLAYER+news", 5), ("TEAM-Elo baseline", 1)):
    a, b = ols([r[xi] for r in rows_fit], [r[2] for r in rows_fit])
    la, lb = logistic_fit([r[xi] for r in rows_fit], [r[3] for r in rows_fit])
    for sub, tag in ((rows_test, "ALL  "), ([r for r in rows_test if r[4]], "SHOCK"), ([r for r in rows_test if not r[4]], "calm ")):
        mae = statistics.mean(abs(a * r[xi] + b - r[2]) for r in sub)
        acc = statistics.mean(((a * r[xi] + b > 0) == (r[2] > 0)) for r in sub)
        print(f"{label:18} {tag} n={len(sub):>3} MAE={mae:.2f} side-acc={acc:.1%}")
