#!/usr/bin/env python
"""WHY does an overshoot-over miss even though the line is already discounted below median?
For each graded overshoot-over: actual stat, minutes played vs usual, game total, blowout
margin, and how far it finished under its median. Split STAR vs ROLE and HIT vs MISS to
find the mechanism. Pure stdlib."""
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
    hs, a = fnum(r.get("home_score")), fnum(r.get("away_score"))
    games[r["game_id"]] = dict(date=nd(r.get("date", "")),
                               tot=(hs + a if hs is not None and a is not None else None),
                               marg=(abs(hs - a) if hs is not None and a is not None else None))

log = defaultdict(list)
bygame = {}
for r in csv.DictReader(open("data/box_2026.csv", encoding="utf-8")):
    g = games.get(r["game_id"])
    if not g or not g["date"]:
        continue
    try:
        log[r["player"].lower()].append((g["date"], float(r["pts"]), float(r["reb"]), float(r["ast"]), float(r["min"])))
    except (ValueError, TypeError):
        continue
    bygame[(r["player"].lower(), g["date"])] = (r, g)

pick = {"pts": lambda x: x[1], "pr": lambda x: x[1] + x[2], "pa": lambda x: x[1] + x[3],
        "ra": lambda x: x[2] + x[3], "pra": lambda x: x[1] + x[2] + x[3], "ast": lambda x: x[3], "reb": lambda x: x[2]}

bets = []
for r in csv.DictReader(open("graded_bets.csv", encoding="utf-8")):
    if r.get("src") != "overshoot" or r.get("side") != "Over" or r.get("market") not in pick:
        continue
    res = r.get("result", "")
    if res not in ("WIN", "loss", "LOSS"):
        continue
    plow, bdate, mk = r["player"].lower(), nd(r["date"]), r["market"]
    actual, line = fnum(r.get("actual")), fnum(r.get("line"))
    bg = bygame.get((plow, bdate))
    if bg is None or actual is None or line is None:
        continue
    box, g = bg
    prior = sorted([x for x in log[plow] if x[0] < bdate])
    if len(prior) < 4:
        continue
    med = statistics.median([pick[mk](x) for x in prior][-10:])
    med_min = statistics.median([x[4] for x in prior][-10:])
    amin = fnum(box.get("min"))
    bets.append(dict(p=r["player"], mk=mk, line=line, actual=actual, med=med, win=(res == "WIN"),
                     amin=amin, dmin=(amin - med_min if amin is not None and med_min else None),
                     under_med=med - actual, tot=g["tot"], marg=g["marg"], star=(med >= 18)))


def avg(items, k):
    xs = [b[k] for b in items if b.get(k) is not None]
    return sum(xs) / len(xs) if xs else float("nan")


def rec(items):
    n = len(items); w = sum(b["win"] for b in items)
    return f"{w}-{n - w}"


print(f"overshoot-overs analyzed: {len(bets)}\n")
print("=== STAR vs ROLE  x  HIT vs MISS — what's different? ===")
print(f"{'group':<18}{'n':>3}{'min vs usual':>13}{'finished vs med':>16}{'game total':>12}{'margin':>8}")
for who, isstar in [("STAR (med≥18)", True), ("ROLE (med<18)", False)]:
    grp = [b for b in bets if b["star"] == isstar]
    print(f"  {who} — {rec(grp)}")
    for lab, items in [("  over HIT", [b for b in grp if b["win"]]), ("  over MISS", [b for b in grp if not b["win"]])]:
        if items:
            print(f"  {lab:<16}{len(items):>3}{avg(items,'dmin'):>+13.1f}{avg(items,'under_med'):>+16.1f}{avg(items,'tot'):>12.0f}{avg(items,'marg'):>8.0f}")

print("\n=== EVERY overshoot-over (misses tell the story) ===")
print(f"{'player':<19}{'mk':<4}{'line':>5}{'med':>6}{'got':>6}{'min±':>6}{'tot':>5}{'marg':>6}  result")
for b in sorted(bets, key=lambda b: (not b["star"], b["win"])):
    dm = f"{b['dmin']:+.0f}" if b['dmin'] is not None else "  ?"
    tg = "★" if b["star"] else "·"
    print(f"{tg}{b['p'][:18]:<18}{b['mk']:<4}{b['line']:>5.1f}{b['med']:>6.1f}{b['actual']:>6.1f}{dm:>6}"
          f"{(b['tot'] or 0):>5.0f}{(b['marg'] or 0):>6.0f}  {'WIN ' if b['win'] else 'MISS'}")
