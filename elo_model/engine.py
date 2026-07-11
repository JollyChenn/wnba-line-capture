# engine.py - Phase 2: player O/D ratings over 2023-2026 (stdlib only, no pandas).
# Ratings live in Z-UNITS (0 = league average, +1 = one league-sd above) - simpler than 1500-Elo and
# converts directly to points later. Chronological single pass (walk-forward: never sees the future).
#
# OFFENSE per game: per-36 composite of the user's variables -
#   scoring value  = pts - lgTS%*2*(fga+0.44*fta)   (efficiency x volume vs league)
#   creation       = 0.7*ast - 1.0*to               (turnover = the liability term)
#   rebound value  = 0.7*oreb + 0.3*dreb
#   stocks (D box) = feed the D rating, not offense
# actual_z = (composite36 - lg_mean)/lg_sd, clipped +-2.5 (blowout/garbage damper)
# expected_z = own oR - opponent's minutes-weighted dR (good defense suppresses)
# update: oR += lr * minutes_factor * (actual - expected);  lr decays with games played (Glicko-ish)
#
# DEFENSE per game (box can't see individual D -> team-shared, weakest link, stated openly):
#   team_def_z = (league PPP + opp offensive quality shift - actual opp PPP) / sd(PPP)
#   each player pulled toward team_def_z by minutes share; small stocks bonus (stl+blk per36 z * 0.3)
# Season rollover: r = 0.7*r (regress toward 0). New players start 0 with high lr (rookie prior=avg).
import csv, os, statistics, sys, math
from collections import defaultdict
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

# ---- pass 0: league constants (global; small look-ahead ONLY into league-wide averages, standard) ----
comps, ppps, ts_num, ts_den = [], [], 0.0, 0.0
for g in games:
    rows = box.get(g["game_id"], [])
    for tm in {r["team"] for r in rows}:
        tr = [r for r in rows if r["team"] == tm]
        poss = sum(f(r["fga"]) + 0.44 * f(r["fta"]) + f(r["to"]) - f(r["oreb"]) for r in tr)
        pts = sum(f(r["pts"]) for r in tr)
        if poss > 40: ppps.append(100 * pts / poss)
    for r in rows:
        ts_num += f(r["pts"]); ts_den += 2 * (f(r["fga"]) + 0.44 * f(r["fta"]))
LGTS = ts_num / ts_den                      # league points per shot-attempt*2 (TS baseline)
PPP_M, PPP_SD = statistics.mean(ppps), statistics.pstdev(ppps)
def comp36(r):
    m = f(r["min"])
    if m < 6: return None
    raw = (f(r["pts"]) - LGTS * 2 * (f(r["fga"]) + 0.44 * f(r["fta"]))) \
          + 0.7 * f(r["ast"]) - 1.0 * f(r["to"]) + 0.7 * f(r["oreb"]) + 0.3 * f(r["dreb"]) \
          + 0.15 * (f(r["fga"]) + 0.44 * f(r["fta"]))
    # last term = shot-creation credit: volume at league-avg efficiency beats not shooting
    return raw * 36 / m
for g in games:
    for r in box.get(g["game_id"], []):
        c = comp36(r)
        if c is not None and f(r["min"]) >= 15: comps.append(c)
C_M, C_SD = statistics.mean(comps), statistics.pstdev(comps)
print(f"league: TS-base {LGTS:.3f}, PPP {PPP_M:.1f}±{PPP_SD:.1f}, comp36 {C_M:.2f}±{C_SD:.2f}")

# ---- walk-forward rating pass ----
oR, dR, gp = defaultdict(float), defaultdict(float), defaultdict(int)   # keyed by athlete id
name_of, team_of = {}, {}
season_cur = None
CLIP = 2.5
def lr(g): return 0.28 * 15 / (15 + g) + 0.04          # 0.32 rookie -> ~0.06 veteran

for g in games:
    if g["season"] != season_cur:                       # season rollover regression
        season_cur = g["season"]
        for k in list(oR): oR[k] *= 0.7
        for k in list(dR): dR[k] *= 0.7
    rows = box.get(g["game_id"], [])
    if not rows: continue
    T = defaultdict(list)
    for r in rows: T[r["team"]].append(r)
    if len(T) != 2: continue
    (tA, ra), (tB, rb) = T.items()
    # minutes-weighted team aggregates (pregame ratings)
    def agg(rr, R):
        tm_ = sum(f(r["min"]) for r in rr) or 1
        return sum(R[r["aid"]] * f(r["min"]) for r in rr) / tm_
    dAgg = {tA: agg(ra, dR), tB: agg(rb, dR)}
    oAgg = {tA: agg(ra, oR), tB: agg(rb, oR)}
    # offense updates
    for tm, rr, opp in ((tA, ra, tB), (tB, rb, tA)):
        for r in rr:
            c = comp36(r)
            if c is None: continue
            aid = r["aid"]; name_of[aid] = r["player"]; team_of[aid] = tm
            act = max(-CLIP, min(CLIP, (c - C_M) / C_SD))
            exp = oR[aid] - dAgg[opp]
            mf = min(f(r["min"]) / 30.0, 1.0)
            oR[aid] += lr(gp[aid]) * mf * (act - exp)
        # defense: team-level defensive z shared by minutes
        poss = sum(f(x["fga"]) + 0.44 * f(x["fta"]) + f(x["to"]) - f(x["oreb"]) for x in box[g["game_id"]] if x["team"] == opp)
        opts = sum(f(x["pts"]) for x in box[g["game_id"]] if x["team"] == opp)
        if poss > 40:
            # expected opp PPP shifted by opp offensive quality (z * ~3 PPP per z) minus our D agg
            exp_ppp = PPP_M + oAgg[opp] * 3.0 - dAgg[tm] * 3.0
            dz = max(-CLIP, min(CLIP, (exp_ppp - 100 * opts / poss) / PPP_SD))   # + = held below expectation
            for r in rr:
                aid = r["aid"]; m = f(r["min"])
                if m < 6: continue
                stz = ((f(r["stl"]) + f(r["blk"])) * 36 / m - 1.5) / 1.5          # stocks per36 vs ~1.5 typical
                dR[aid] += lr(gp[aid]) * (m / 200.0) * (dz - dR[aid]) + 0.01 * max(-2, min(2, stz))
        for r in rr:
            if f(r["min"]) >= 6: gp[r["aid"]] += 1

# ---- save + G2 sanity ----
w = csv.writer(open(os.path.join(D, "ratings.csv"), "w", newline="", encoding="utf-8"))
w.writerow(["aid", "player", "team", "gp", "oR", "dR"])
for aid in oR:
    w.writerow([aid, name_of.get(aid), team_of.get(aid), gp[aid], round(oR[aid], 3), round(dR[aid], 3)])
act26 = [a for a in oR if gp[a] >= 100 or (gp[a] >= 15 and team_of.get(a))]
top = sorted([a for a in oR if gp[a] >= 30], key=lambda a: -oR[a])[:12]
print("\nG2 TOP-12 OFFENSE (min 30 gp):")
for a in top: print(f"  {name_of[a]:24}{team_of[a]:5}oR={oR[a]:+.2f} dR={dR[a]:+.2f} gp={gp[a]}")
topd = sorted([a for a in dR if gp[a] >= 30], key=lambda a: -dR[a])[:8]
print("G2 TOP-8 DEFENSE:")
for a in topd: print(f"  {name_of[a]:24}{team_of[a]:5}dR={dR[a]:+.2f} oR={oR[a]:+.2f} gp={gp[a]}")
print(f"\nrating sd across {len(top and oR)} players: o={statistics.pstdev(oR.values()):.2f} d={statistics.pstdev(dR.values()):.2f}")
