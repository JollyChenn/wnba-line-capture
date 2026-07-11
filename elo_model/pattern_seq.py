# pattern_seq.py - the user's sequence/streak/H2H pattern hunt, walk-forward, with significance.
# Q1 totals reversion: after k straight LOW-total games (below team's running median), is the next
#    game's total higher than the team's running mean? (and mirror for HIGH)
# Q2 win-streaks: after a k-game win streak, does the next game under/over-perform the Elo expectation?
# Q3 H2H: do previous meetings this-season predict the next meeting's total beyond team paces?
import csv, os, statistics, math, sys
from collections import defaultdict
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
def f(x):
    try: return float(x)
    except Exception: return 0.0
games = sorted(csv.DictReader(open(os.path.join(D, "games_full.csv"), encoding="utf-8")),
               key=lambda g: (g["date"], g["game_id"]))
tot_hist = defaultdict(list)      # team -> totals so far (season-scoped)
res_hist = defaultdict(list)      # team -> W/L so far
telo = defaultdict(lambda: 1500.0)
season = None
q1 = defaultdict(list)            # ("low",k) -> next_total - running_mean
q2 = defaultdict(list)            # k -> actual_win - elo_expected
h2h_rows = []                     # (h2h_prev_avg_total - lgmean_so_far, this_total - teams_mean)
pair_hist = defaultdict(list)
lg_totals = []
for g in games:
    if g["season"] != season:
        season = g["season"]; tot_hist.clear(); res_hist.clear(); pair_hist.clear()
        for k in list(telo): telo[k] = 1500 + 0.7 * (telo[k] - 1500)
    if not g["home_score"]: continue
    home, away, gid = g["home"], g["away"], g["game_id"]
    total = f(g["home_score"]) + f(g["away_score"]); margin = f(g["home_score"]) - f(g["away_score"])
    # ---- Q1 (evaluate BEFORE appending) ----
    for tm in (home, away):
        h = tot_hist[tm]
        if len(h) >= 6:
            med, mean = statistics.median(h), statistics.mean(h)
            for k in (2, 3, 4):
                if len(h) >= k and all(x < med for x in h[-k:]): q1[("low", k)].append(total - mean)
                if len(h) >= k and all(x > med for x in h[-k:]): q1[("high", k)].append(total - mean)
    # ---- Q2 ----
    eh = 1 / (1 + 10 ** (-(telo[home] + 80 - telo[away]) / 400))
    for tm, won, pw in ((home, margin > 0, eh), (away, margin < 0, 1 - eh)):
        r = res_hist[tm]
        for k in (2, 3, 4):
            if len(r) >= k and all(r[-k:]): q2[k].append((1 if won else 0) - pw)
        for k in (2, 3):
            if len(r) >= k and not any(r[-k:]): q2[-k].append((1 if won else 0) - pw)
    # ---- Q3 ----
    key = tuple(sorted((home, away)))
    if pair_hist[key] and len(lg_totals) > 50:
        lgm = statistics.mean(lg_totals[-200:])
        both = tot_hist[home][-8:] + tot_hist[away][-8:]
        tmm = statistics.mean(both) if both else lgm
        h2h_rows.append((statistics.mean(pair_hist[key]) - tmm, total - tmm))
    # ---- update ----
    mov = (abs(margin) + 3) ** 0.8 / (7.5 + 0.006 * abs(telo[home] + 80 - telo[away]))
    d = 20 * mov * ((1 if margin > 0 else 0) - eh)
    telo[home] += d; telo[away] -= d
    tot_hist[home].append(total); tot_hist[away].append(total)
    res_hist[home].append(margin > 0); res_hist[away].append(margin < 0)
    pair_hist[key].append(total); lg_totals.append(total)

print("Q1 TOTALS after streaks of low/high games (delta vs team running mean; + = next game higher):")
for k, v in sorted(q1.items()):
    m = statistics.mean(v); se = statistics.pstdev(v) / math.sqrt(len(v))
    print(f"  after {k[1]} {k[0]:4}-total games: next {m:+5.1f} pts vs mean  n={len(v):>4} z={m/se:+.1f}")
print("Q2 WIN/LOSS streaks (actual next-win minus Elo-expected; + = streak teams over-deliver):")
for k, v in sorted(q2.items()):
    m = statistics.mean(v); se = statistics.pstdev(v) / math.sqrt(len(v))
    lbl = f"{k}-win" if k > 0 else f"{-k}-loss"
    print(f"  after {lbl:6} streak: {m:+.3f}  n={len(v):>4} z={m/se:+.1f}")
if len(h2h_rows) > 30:
    r = statistics.correlation([x[0] for x in h2h_rows], [x[1] for x in h2h_rows])
    print(f"Q3 H2H: corr(prev-meetings-total-resid, this-total-resid) = {r:+.3f}  n={len(h2h_rows)}")
