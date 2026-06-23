#!/usr/bin/env python
"""Brute-force filter combos on the FULL backtest universe (every rotation player-game, ~1.3k),
not the bot's 87 flagged bets. Each game = an over/under vs its trailing-10 median (synthetic
anchor). Search every single/pair/triplet of PRE-GAME features for the highest win rate on its
best side, then a SHUFFLE CONTROL (random labels) to see what chance produces with this much data.
CAVEAT: vs the MEDIAN, not the book — proves the SIDE, not that it beats the line. Pure stdlib."""
import bisect
import csv
import itertools
import random
import statistics
import sys
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
random.seed(11)


def nd(d):
    return ''.join(c for c in str(d) if c.isdigit())[:8]


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


gmeta, team_pa = {}, defaultdict(list)
for r in csv.DictReader(open("data/games_2026.csv", encoding="utf-8")):
    date, home, away = nd(r.get("date", "")), r.get("home"), r.get("away")
    gmeta[r["game_id"]] = (date, home, away)
    hs, a = fnum(r.get("home_score")), fnum(r.get("away_score"))
    if hs is not None and a is not None:
        team_pa[home].append((date, a))
        team_pa[away].append((date, hs))
for t in team_pa:
    team_pa[t].sort()


def opp_def(team, date):
    pa = [p for d, p in team_pa.get(team, []) if d < date]
    return statistics.mean(pa[-10:]) if len(pa) >= 3 else None


log = defaultdict(list)
for r in csv.DictReader(open("data/box_2026.csv", encoding="utf-8")):
    meta = gmeta.get(r["game_id"])
    if not meta:
        continue
    date, home, away = meta
    team = r["team"]
    opp = away if team == home else (home if team == away else None)
    try:
        log[r["player"].lower()].append((date, float(r["pts"]), float(r["min"]), opp, team == home))
    except (ValueError, TypeError):
        pass
for pl in log:
    log[pl].sort(key=lambda t: t[0])

raw = []
for pl, gl in log.items():
    pts = [g[1] for g in gl]
    mins = [g[2] for g in gl]
    if len(gl) < 6 or statistics.mean(pts) < 8:
        continue
    for i in range(5, len(gl)):
        med = statistics.median(pts[max(0, i - 10):i])
        if med < 8:
            continue
        t3 = statistics.mean(pts[i - 3:i])
        t5m, t10m = statistics.mean(mins[max(0, i - 5):i]), statistics.mean(mins[max(0, i - 10):i])
        med_prev = statistics.median(pts[max(0, i - 11):i - 1]) if i >= 2 else med
        win10 = pts[max(0, i - 10):i]                    # TRAILING only — no lookahead
        tcv = statistics.pstdev(win10) / statistics.mean(win10) if statistics.mean(win10) else 0
        raw.append(dict(
            hot=t3 >= med + 3, cold=t3 <= med - 3,
            shrink=(t5m - t10m) <= -3, expand=(t5m - t10m) >= 3,
            last_big_over=pts[i - 1] >= med_prev + 8, last_big_under=pts[i - 1] <= med_prev - 8,
            home=gl[i][4], away=not gl[i][4],
            star=med >= 15, role=med < 12, _tcv=tcv,
            _od=opp_def(gl[i][3], gl[i][0]),
            under=1 if pts[i] < med else 0, over=1 if pts[i] > med else 0))

ods = sorted(o["_od"] for o in raw if o["_od"] is not None)
t1, t2 = ods[len(ods) // 3], ods[2 * len(ods) // 3]
cvthr = statistics.median([o["_tcv"] for o in raw])      # threshold from TRAILING cv (no per-game lookahead)
for o in raw:
    o["opp_tough"] = o["_od"] is not None and o["_od"] <= t1
    o["opp_weak"] = o["_od"] is not None and o["_od"] >= t2
    o["steady"] = o["_tcv"] < cvthr
    o["volatile"] = o["_tcv"] >= cvthr

FEATS = ["hot", "cold", "shrink", "expand", "last_big_over", "last_big_under", "home", "away",
         "steady", "volatile", "star", "role", "opp_tough", "opp_weak"]
N = len(raw)
under = [o["under"] for o in raw]
over = [o["over"] for o in raw]
base_u = sum(under) / N
fset = {ft: set(i for i, o in enumerate(raw) if o[ft]) for ft in FEATS}

N_MIN = 60
combos = []
for k in (1, 2, 3):
    for c in itertools.combinations(FEATS, k):
        idx = set(range(N))
        for ft in c:
            idx &= fset[ft]
            if len(idx) < N_MIN:
                break
        if len(idx) >= N_MIN:
            combos.append((c, list(idx)))

print(f"{N} player-games · base under-rate {base_u*100:.0f}% · {len(combos)} combos (n>={N_MIN}) searched\n")


def best_rate(U, O):
    best = (None, 0, 0, "")
    for c, idx in combos:
        n = len(idx)
        u = sum(U[i] for i in idx) / n
        ov = sum(O[i] for i in idx) / n
        r, side = (u, "UNDER") if u >= ov else (ov, "OVER")
        if r > best[1]:
            best = (c, r, n, side)
    return best

bc, br, bn, bs = best_rate(under, over)
print("BEST real combo (vs median):")
print(f"  {br*100:.0f}% {bs}  (n={bn})  ::  {' & '.join(bc)}\n")
# show a few top
ranked = sorted(((c, len(idx), sum(under[i] for i in idx) / len(idx), sum(over[i] for i in idx) / len(idx))
                 for c, idx in combos), key=lambda x: max(x[2], x[3]), reverse=True)
print("top combos:")
for c, n, u, o in ranked[:6]:
    r, s = (u, "UNDER") if u >= o else (o, "OVER")
    print(f"  {r*100:4.0f}% {s:<5} n={n:<4} :: {' & '.join(c)}")

K = 300
order = list(range(N))
sh = []
for _ in range(K):
    random.shuffle(order)
    U = [under[order[i]] for i in range(N)]
    O = [over[order[i]] for i in range(N)]
    sh.append(best_rate(U, O)[1])
sh.sort()
pctl = 100 * bisect.bisect_left(sh, br) / K
print(f"\nSHUFFLE CONTROL ({K}× random labels) — best win-rate chance finds with this data:")
print(f"  median {statistics.median(sh)*100:.0f}% · 95th pct {sh[int(0.95*K)]*100:.0f}% · max {sh[-1]*100:.0f}%")
print(f"  REAL best {br*100:.0f}%  →  beats {pctl:.0f}% of random searches")
print("  VERDICT: " + ("REAL SIDE-PREDICTOR — clears the chance ceiling (still vs median, needs the book/CLV test)"
                       if pctl >= 95 else f"OVERFIT — chance alone hits this ({pctl:.0f}th pct of noise). No real combo even at full power."))
