#!/usr/bin/env python
"""For every GRADED book-overshoot OVER, reconstruct the line vs the player's trailing-10
median at bet time (the DEPTH of the discount) + form/minutes 'trap tell', and see what hit.
Answers: is a line set far BELOW a player's median (e.g. median 15, line 9) a value-over or a trap?"""
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


gd = {r["game_id"]: nd(r.get("date", "")) for r in csv.DictReader(open("data/games_2026.csv", encoding="utf-8"))}
log = defaultdict(list)
for r in csv.DictReader(open("data/box_2026.csv", encoding="utf-8")):
    try:
        log[r["player"].lower()].append((gd.get(r["game_id"], ""), float(r["pts"]), float(r["reb"]), float(r["ast"]), float(r["min"])))
    except (ValueError, TypeError):
        pass

pick = {"pts": lambda x: x[1], "pr": lambda x: x[1] + x[2], "pa": lambda x: x[1] + x[3], "pra": lambda x: x[1] + x[2] + x[3]}

bets = []
for r in csv.DictReader(open("graded_bets.csv", encoding="utf-8")):
    if r.get("src") != "overshoot" or r.get("side") != "Over":
        continue
    res = r.get("result", "")
    if res not in ("WIN", "loss", "LOSS"):
        continue
    plow, mk = r["player"].lower(), r["market"]
    if mk not in pick:
        continue
    try:
        line = float(r["line"])
    except ValueError:
        continue
    g = sorted([x for x in log.get(plow, []) if x[0] and x[0] < nd(r["date"])], key=lambda t: t[0])
    v = [pick[mk](x) for x in g]
    b = dict(p=r["player"], mk=mk, line=line, win=(res == "WIN"), med=None)
    if len(v) >= 4:
        v10 = v[-10:]
        med = statistics.median(v10)
        t3 = statistics.mean(v[-3:])
        mins = [x[4] for x in g]
        t5m, t10m = statistics.mean(mins[-5:]), statistics.mean(mins[-min(10, len(mins)):])
        b.update(med=med, depth=med - line, dpct=line / med if med else None,
                 form=("HOT" if t3 >= med + 3 else "COLD" if t3 <= med - 3 else "steady"),
                 mtr=("exp" if t5m - t10m >= 3 else "shrink" if t5m - t10m <= -3 else "flat"))
    bets.append(b)

usable = [b for b in bets if b.get("med")]


def rate(items):
    n = len(items)
    w = sum(1 for b in items if b["win"])
    return f"{w}-{n - w} ({100 * w / n:.0f}% over)" if n else "—"


print(f"overshoot-OVER bets matched to box history: {len(usable)} / {len(bets)}\n")
print("BY DEPTH BELOW MEDIAN (median − line):")
for lab, t in [("shallow  3–5", lambda b: 3 <= b["depth"] < 5),
               ("medium   5–8", lambda b: 5 <= b["depth"] < 8),
               ("DEEP     8+ ", lambda b: b["depth"] >= 8)]:
    print(f"  {lab:<14} {rate([b for b in usable if t(b)])}")

print("\nBY DISCOUNT % (line as a share of median):")
for lab, t in [("≥75% of med (mild)", lambda b: b["dpct"] >= 0.75),
               ("60–75% (steep)", lambda b: 0.60 <= b["dpct"] < 0.75),
               ("<60% (drastic, e.g. 15→9)", lambda b: b["dpct"] < 0.60)]:
    print(f"  {lab:<28} {rate([b for b in usable if t(b)])}")

print("\nBY THE TRAP TELL (form + minutes at bet time):")
trap = [b for b in usable if b["form"] == "COLD" or b["mtr"] == "shrink"]
ok = [b for b in usable if not (b["form"] == "COLD" or b["mtr"] == "shrink")]
print(f"  ⚠ COLD or SHRINKING mins (book may be right): {rate(trap)}")
print(f"  ✅ hot/steady + stable/expanding mins:         {rate(ok)}")

print("\nEVERY overshoot-over (deepest discount first):")
for b in sorted(usable, key=lambda b: b["dpct"]):
    print(f"  {b['p'][:19]:<19} {b['mk']:<3} O{b['line']:<5} | med {b['med']:5.1f} | {b['depth']:4.1f} below ({b['dpct']*100:3.0f}% of med) | "
          f"{b['form']:<6} {b['mtr']:<6} -> {'WIN ' if b['win'] else 'loss'}")
