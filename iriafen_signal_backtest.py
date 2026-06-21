# iriafen_signal_backtest.py — does the model's cold+shrink UNDER signal still work when the SHRINK is driven
# by a single low-minute outlier game (Iriafen's case: minutes [27,27,27,8,28] -> the 8 created the 'shrink')?
# Replays the signal across every player-game in box_2026 and splits OUTLIER-DRIVEN vs CLEAN decline.
# Under-hit proxy: actual < the trailing-10 median (the model anchors its line on that median). Read-only.
import csv, statistics
from collections import defaultdict

gd = {r["game_id"]: r.get("date") for r in csv.DictReader(open("data/games_2026.csv", encoding="utf-8"))}
log = defaultdict(list)
for r in csv.DictReader(open("data/box_2026.csv", encoding="utf-8")):
    d = gd.get(r["game_id"])
    if not d:
        continue
    try:
        log[r["player"].lower()].append((d, float(r["pts"]), float(r["reb"]), float(r["ast"]), float(r["min"])))
    except (ValueError, TypeError):
        pass

MK = {"pts": lambda x: x[1], "pr": lambda x: x[1] + x[2], "pa": lambda x: x[1] + x[3],
      "ra": lambda x: x[2] + x[3], "pra": lambda x: x[1] + x[2] + x[3]}
mean = lambda xs: sum(xs) / len(xs)
res = defaultdict(lambda: [0, 0])     # (market, group) -> [under_hits, total]

for player, games in log.items():
    games.sort()
    for i in range(10, len(games)):
        prior = games[:i]
        mins = [g[4] for g in prior]
        m5, m10 = mean(mins[-5:]), mean(mins[-10:-5])
        if not (m5 <= m10 - 3):                       # SHRINK must fire
            continue
        last5 = mins[-5:]
        wo = last5[:]; wo.remove(min(last5))          # drop the single lowest-minute game
        outlier = mean(wo) > m10 - 3                  # shrink ONLY holds because of that one game = outlier-driven
        grp = "OUTLIER-driven" if outlier else "CLEAN decline"
        for mk, f in MK.items():
            v = [f(g) for g in prior]
            med = statistics.median(v[-10:])
            if not (mean(v[-3:]) <= med - 4):          # COLD must fire (2-of-3 model under)
                continue
            hit = f(games[i]) < med                    # under (at the median line) hit?
            res[(mk, grp)][0] += hit; res[(mk, grp)][1] += 1
            res[("ALL", grp)][0] += hit; res[("ALL", grp)][1] += 1

print("cold+shrink UNDER signal — does a one-game-outlier shrink perform worse than a clean decline?\n")
print(f"{'market':8}{'group':16}{'under-hit':>12}{'n':>6}")
for mk in ["ALL", "pts", "pra", "pr", "pa", "ra"]:
    for grp in ["CLEAN decline", "OUTLIER-driven"]:
        h, n = res[(mk, grp)]
        if n:
            print(f"{mk:8}{grp:16}{h}/{n} = {h/n*100:4.0f}%{'':3}{n:>4}")
    print()
# headline gap
ch, cn = res[("ALL", "CLEAN decline")]
oh, on = res[("ALL", "OUTLIER-driven")]
if cn and on:
    print(f"OVERALL: clean {ch/cn*100:.0f}% (n={cn}) vs outlier {oh/on*100:.0f}% (n={on}) "
          f"-> gap {ch/cn*100 - oh/on*100:+.0f} pts (>0 = outlier signal is WORSE = model gets fooled)")
print("\n(breakeven for an under bet at ~1.85 odds = ~54%; under-hit here is vs the median line, a proxy.)")
