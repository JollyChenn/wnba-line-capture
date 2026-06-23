#!/usr/bin/env python
"""(A) The TRANSITION pattern: after game-1 was X above/below a player's usual, what does
game-2 do — drop, rise, or hold? (regression to the mean, quantified). (B) Does the OPPONENT
they face move it? Pure stdlib."""
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


gmeta = {}
team_pa = defaultdict(list)                                # team -> [(date, points allowed)]
for r in csv.DictReader(open("data/games_2026.csv", encoding="utf-8")):
    date, home, away = nd(r.get("date", "")), r.get("home"), r.get("away")
    gmeta[r["game_id"]] = (date, home, away)
    try:
        hs, a = float(r["home_score"]), float(r["away_score"])
        team_pa[home].append((date, a))                    # home's defense allowed away_score
        team_pa[away].append((date, hs))
    except (ValueError, TypeError):
        pass
for t in team_pa:
    team_pa[t].sort()


def opp_def(team, date):
    pa = [p for d, p in team_pa.get(team, []) if d < date]
    return statistics.mean(pa[-10:]) if len(pa) >= 3 else None


log = defaultdict(list)                                    # player -> [(date, pts, opp)]
for r in csv.DictReader(open("data/box_2026.csv", encoding="utf-8")):
    meta = gmeta.get(r["game_id"])
    if not meta:
        continue
    date, home, away = meta
    team = r["team"]
    opp = away if team == home else (home if team == away else None)
    try:
        log[r["player"].lower()].append((date, float(r["pts"]), opp))
    except (ValueError, TypeError):
        pass
for pl in log:
    log[pl].sort(key=lambda t: t[0])

# A) transition / reversion
trans = []
for pl, gl in log.items():
    pts = [g[1] for g in gl]
    if len(pts) < 6 or statistics.mean(pts) < 8:
        continue
    for i in range(4, len(pts) - 1):
        avg = statistics.mean(pts[max(0, i - 10):i])
        trans.append((pts[i] - avg, pts[i + 1] - avg, pts[i], pts[i + 1]))

print("=== A) THE TRANSITION: game-1 vs the player's usual  ->  what game-2 does ===")
print(f"{'game-1 was…':<24}{'n':>5}{'avg G1':>8}{'avg G2':>8}{'G2 vs usual':>14}{'reverted':>10}")
for lab, t in [("BIG over (+8 or more)", lambda d: d >= 8), ("mild over (+3..8)", lambda d: 3 <= d < 8),
               ("about usual (±3)", lambda d: -3 < d < 3), ("mild under (-8..-3)", lambda d: -8 < d <= -3),
               ("BIG under (-8 or more)", lambda d: d <= -8)]:
    g = [x for x in trans if t(x[0])]
    if not g:
        continue
    di, dn = statistics.mean([x[0] for x in g]), statistics.mean([x[1] for x in g])
    rev = f"{(1 - dn / di) * 100:.0f}%" if abs(di) > 0.5 else "—"
    print(f"{lab:<24}{len(g):>5}{statistics.mean([x[2] for x in g]):>8.1f}"
          f"{statistics.mean([x[3] for x in g]):>8.1f}{dn:>+14.1f}{rev:>10}")

# B) opponent
rows = []
for pl, gl in log.items():
    pts = [g[1] for g in gl]
    if len(pts) < 6 or statistics.mean(pts) < 8:
        continue
    for i in range(4, len(gl)):
        od = opp_def(gl[i][2], gl[i][0]) if gl[i][2] else None
        if od is not None:
            rows.append((od, pts[i] - statistics.mean(pts[max(0, i - 10):i])))
ods = sorted(x[0] for x in rows)
t1, t2 = ods[len(ods) // 3], ods[2 * len(ods) // 3]
print(f"\n=== B) OPPONENT DEFENSE: does who they face matter?  (matched {len(rows)} player-games) ===")
print(f"  league avg pts allowed ≈ {statistics.mean(ods):.0f}/game")
print(f"{'opponent defense':<30}{'n':>5}{'player pts vs their usual':>27}")
for lab, t in [(f"TOUGH D (allows ≤{t1:.0f})", lambda od: od <= t1),
               ("average D", lambda od: t1 < od < t2),
               (f"WEAK D (allows ≥{t2:.0f})", lambda od: od >= t2)]:
    g = [x for x in rows if t(x[0])]
    if g:
        print(f"  {lab:<28}{len(g):>5}{statistics.mean([x[1] for x in g]):>+26.2f}")
