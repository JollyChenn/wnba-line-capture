#!/usr/bin/env python
"""Hypothesis hunt (pre-backtest): WHY does a prop go over vs under?
For every graded bet, join the player's actual game (minutes, the box) + the game
environment (total points, blowout margin) and see what separates WINS from LOSSES,
split by Over/Under. Looking for a fundamental driver, not just price."""
import csv
import statistics
import sys
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def nd(d):
    return ''.join(c for c in str(d) if c.isdigit())[:8]


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


games = {}
for r in csv.DictReader(open("data/games_2026.csv", encoding="utf-8")):
    hs, as_ = fnum(r.get("home_score")), fnum(r.get("away_score"))
    games[r["game_id"]] = dict(date=nd(r.get("date", "")),
                               tot=(hs + as_ if hs is not None and as_ is not None else None),
                               marg=(abs(hs - as_) if hs is not None and as_ is not None else None))

log = defaultdict(list)            # player -> [(date, pts, reb, ast, min)]
bygame = {}                        # (player, date) -> (box row, game)
for r in csv.DictReader(open("data/box_2026.csv", encoding="utf-8")):
    g = games.get(r["game_id"])
    if not g or not g["date"]:
        continue
    try:
        log[r["player"].lower()].append((g["date"], float(r["pts"]), float(r["reb"]), float(r["ast"]), float(r["min"])))
    except (ValueError, TypeError):
        continue
    bygame[(r["player"].lower(), g["date"])] = (r, g)

pick = {"pts": lambda x: x[1], "pr": lambda x: x[1] + x[2], "pa": lambda x: x[1] + x[3], "pra": lambda x: x[1] + x[2] + x[3]}

bets = []
for r in csv.DictReader(open("graded_bets.csv", encoding="utf-8")):
    res = r.get("result", "")
    if res not in ("WIN", "loss", "LOSS") or r.get("market") not in pick:
        continue
    plow, bdate, mk = r["player"].lower(), nd(r["date"]), r["market"]
    bg = bygame.get((plow, bdate))
    if not bg:
        continue
    box, g = bg
    prior = sorted([x for x in log[plow] if x[0] < bdate])
    if len(prior) < 3:
        continue
    mins = [x[4] for x in prior]
    med_min = statistics.median(mins[-10:])
    try:
        amin = float(box["min"])
    except (ValueError, TypeError):
        continue
    bets.append(dict(side=r["side"], win=1 if res == "WIN" else 0, amin=amin,
                     minratio=(amin / med_min if med_min else None), med_min=med_min,
                     tot=g["tot"], marg=g["marg"], clv=fnum(r.get("odds_clv"))))

print(f"matched {len(bets)} graded bets to their actual game\n")


def rate(items):
    n = len(items)
    w = sum(b["win"] for b in items)
    return f"{w}-{n - w} ({100 * w / n:.0f}%)" if n else "—"


def avg(items, k):
    xs = [b[k] for b in items if b.get(k) is not None]
    return sum(xs) / len(xs) if xs else float("nan")


print("=== GROUP MEANS — what separates a WIN from a LOSS? ===")
print(f"{'group':<16}{'n':>4}{'min played':>12}{'min ratio':>11}{'game total':>12}{'margin':>9}")
for side in ["Over", "Under"]:
    s = [b for b in bets if b["side"] == side]
    for lab, items in [("WON", [b for b in s if b["win"]]), ("LOST", [b for b in s if not b["win"]])]:
        print(f"{side+' '+lab:<16}{len(items):>4}{avg(items,'amin'):>12.1f}{avg(items,'minratio'):>11.2f}"
              f"{avg(items,'tot'):>12.0f}{avg(items,'marg'):>9.0f}")

print("\n=== SINGLE-FEATURE SPLITS (median cut) — Over vs Under hit rate ===")


def med_of(key):
    xs = sorted(b[key] for b in bets if b.get(key) is not None)
    return statistics.median(xs) if xs else None


for key, label, lo, hi in [("minratio", "MINUTES vs usual", "played LESS", "played FULL+"),
                           ("tot", "GAME TOTAL", "LOW-scoring", "HIGH-scoring"),
                           ("marg", "FINAL MARGIN", "CLOSE game", "BLOWOUT")]:
    m = med_of(key)
    print(f"\n {label} (cut at {m:.1f}):")
    for side in ["Over", "Under"]:
        loi = [b for b in bets if b["side"] == side and b.get(key) is not None and b[key] < m]
        hii = [b for b in bets if b["side"] == side and b.get(key) is not None and b[key] >= m]
        print(f"   {side:<6} {lo}: {rate(loi):<14}  {hi}: {rate(hii)}")
