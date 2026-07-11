# zone_matchup.py - the user's style/heat-map layer, team-level v1, walk-forward.
# Zones from shots.csv (hoop at x=25,y=5.25): rim<6ft, paint<14, mid, corner3 (y<10), arc3.
# OFFENSE profile per team: decayed attempt-SHARE + pts-per-attempt (ppa) per zone.
# DEFENSE suppression per team per zone: decayed (opp actual ppa - that opp's usual ppa) = how much
#   this defense bends shooters BELOW their own habit in that zone (the user's corner example).
# MATCHUP feature for a game: sum_z offense_share_z * def_suppression_z * attempts (=points shift),
#   home-minus-away -> 2nd regressor next to player-strength diff. Judge: does TEST MAE drop?
import csv, os, math, statistics, sys
from collections import defaultdict
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
def f(x):
    try: return float(x)
    except Exception: return 0.0

def zone(x, y, three):
    if three: return "c3" if y < 10 else "a3"
    d = math.hypot(x - 25, y - 5.25)
    return "rim" if d < 6 else ("paint" if d < 14 else "mid")
ZONES = ("rim", "paint", "mid", "c3", "a3")
PTS = {"rim": 2, "paint": 2, "mid": 2, "c3": 3, "a3": 3}

# team abbrev per game from games_full; shots have team_id (ESPN numeric) -> map via box? shots lack abbrev.
# Map team_id->abbrev using majority vote per game side: skip - instead aggregate shots per game via shooter->team from box.
games = sorted(csv.DictReader(open(os.path.join(D, "games_full.csv"), encoding="utf-8")),
               key=lambda g: (g["date"], g["game_id"]))
p2t = defaultdict(dict)                                 # game_id -> player name -> team
for r in csv.DictReader(open(os.path.join(D, "box_full.csv"), encoding="utf-8")):
    p2t[r["game_id"]][r["player"]] = r["team"]
gz = defaultdict(lambda: defaultdict(lambda: [0, 0]))   # game_id -> (team,zone) -> [att, pts]
for r in csv.DictReader(open(os.path.join(D, "shots.csv"), encoding="utf-8")):
    tm = p2t.get(r["game_id"], {}).get(r["shooter"])
    if not tm: continue
    z = zone(f(r["x"]), f(r["y"]), r["three"] == "1")
    c = gz[r["game_id"]][(tm, z)]
    c[0] += 1; c[1] += PTS[z] * (r["made"] == "1")

DEC = 0.93                                              # decay per game (~10-game half-life)
off = defaultdict(lambda: {z: [1.0 * s, 1.0] for z, s in zip(ZONES, (0.30, 0.15, 0.15, 0.08, 0.32))})
# off[team][zone] = [decayed att, decayed weight-games]; ppa tracked separately
offp = defaultdict(lambda: {z: [1.0, 1.0] for z in ZONES})   # [decayed pts, decayed att]
dsup = defaultdict(lambda: {z: [0.0, 1.0] for z in ZONES})   # [decayed (ppa_allowed - opp_usual)*att, att]
feats = []                                              # (matchup_diff, margin, season)  walk-forward
for g in games:
    gid = g["game_id"]; home, away = g["home"], g["away"]
    zrec = gz.get(gid)
    if not zrec or not g["home_score"]: continue
    def mfeat(o, d):                                    # expected pts shift of offense o vs defense d
        tot = sum(off[o][z][0] for z in ZONES) or 1
        return sum((off[o][z][0] / tot) * (dsup[d][z][0] / dsup[d][z][1]) for z in ZONES) * 65
    feats.append((gid, mfeat(home, away) - mfeat(away, home),
                  f(g["home_score"]) - f(g["away_score"]), g["season"]))
    # update walk-forward states AFTER prediction
    for tm, opp in ((home, away), (away, home)):
        for z in ZONES:
            att, pts = zrec.get((tm, z), [0, 0])
            o = off[tm][z]; o[0] = o[0] * DEC + att
            p = offp[tm][z]; p[0] = p[0] * DEC + pts; p[1] = p[1] * DEC + att
            usual = p[0] / p[1]                          # shooter team's own habit ppa (post-update ok: proxy)
            ds = dsup[opp][z]
            ds[0] = ds[0] * DEC + (pts - usual * att)    # negative = suppressed below habit
            ds[1] = ds[1] * DEC + att
print(f"games with zone feature: {len(feats)}")
tr = [x[1:] for x in feats if x[3] in ("2023", "2024")]; te = [x[1:] for x in feats if x[3] in ("2025", "2026")]
xs = [x[0] for x in tr]; ys = [x[1] for x in tr]
mx, my = statistics.mean(xs), statistics.mean(ys)
a = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sum((x - mx) ** 2 for x in xs) or 1)
b = my - a * mx
mae = statistics.mean(abs(a * x[0] + b - x[1]) for x in te)
r = statistics.correlation([x[0] for x in te], [x[1] for x in te]) if len(te) > 2 else 0
print(f"zone-matchup ALONE: fit a={a:.2f} b={b:+.2f} | TEST MAE={mae:.2f} corr(test)={r:+.3f}")
print("(if corr ~0 the style layer has no team-level signal; player-level would be the next attempt)")
csv.writer(open(os.path.join(D, "zone_feats.csv"), "w", newline="")).writerows(
    [("game_id", "matchup_diff", "margin", "season")] + feats)
