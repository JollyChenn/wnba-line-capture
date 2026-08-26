"""Hypothesis C: 3rd foul before halftime -> minutes/points collapse. Mechanism, then next-game."""
import csv, os, sys, math, collections, random, statistics
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
random.seed(20260826)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pbpx_lib import *

meta = {}
for r in csv.DictReader(open(os.path.join(R, "outputs", "gm", "gm_dataset.csv"), encoding="utf-8")):
    meta[r["game_id"]] = (r["date"], int(r["season"]), r["home"], r["away"],
                          int(r["home_score"]), int(r["away_score"]))
P = []
for r in csv.DictReader(open(os.path.join(H, "pbp_players.csv"), encoding="utf-8")):
    m = meta.get(r["game_id"])
    if not m:
        continue
    d, season, home, away, hs, as_ = m
    P.append(dict(gid=r["game_id"], date=d, season=season, player=r["player"],
                  team=(home if r["side"] == "home" else away), side=r["side"],
                  starter=int(r["starter"]), mins=float(r["mins"]), pts=int(r["pts"]),
                  fga=int(r["fga"]), tpa=int(r["tpa"]), nfoul=int(r["nfoul"]),
                  t3=(float(r["t3"]) if r["t3"] else None),
                  t4=(float(r["t4"]) if r["t4"] else None),
                  ft=[float(x) for x in r["ftimes"].split("|") if x]))
P.sort(key=lambda r: (r["season"], r["date"]))
print("player-games: %d over %d games, %d players, seasons %s" %
      (len(P), len(set(r["gid"] for r in P)), len(set(r["player"] for r in P)),
       sorted(set(r["season"] for r in P))))

# fouls by halftime (elapsed < 1200s)
for r in P:
    r["f_h1"] = sum(1 for t in r["ft"] if t < 1200.0)
    r["trouble"] = int(r["f_h1"] >= 3)
    r["t3h1"] = r["t3"] if (r["t3"] is not None and r["t3"] < 1200.0) else None

# walk-forward player-season(-team) baselines
ser = collections.defaultdict(list)
for r in P:
    ser[(r["season"], r["player"], r["team"])].append(r)
for k, v in ser.items():
    v.sort(key=lambda r: r["date"])
    for i, r in enumerate(v):
        pri = [p for p in v[:i] if p["mins"] > 0]
        r["npri"] = len(pri)
        if len(pri) >= 5:
            r["b_min"] = statistics.mean(p["mins"] for p in pri)
            r["b_pts"] = statistics.mean(p["pts"] for p in pri)
            r["b_f"] = statistics.mean(p["nfoul"] for p in pri)
        r["nxt"] = v[i + 1] if i + 1 < len(v) else None

E = [r for r in P if r.get("b_min") is not None]
print("player-games with a >=5-game walk-forward baseline: %d" % len(E))
ST = [r for r in E if r["b_min"] >= 24.0]
print("'star/rotation starter' pool (walk-forward baseline mins >= 24): %d player-games, %d players" %
      (len(ST), len(set(r["player"] for r in ST))))
print("P(3 fouls by halftime | starter pool) = %.4f   (n trouble = %d)" %
      (sum(r["trouble"] for r in ST) / len(ST), sum(r["trouble"] for r in ST)))

print("\n=== MECHANISM: what actually happens to her in THAT game? ===")
print("%-26s %5s %8s %8s %9s %8s %8s %9s" % ("group", "n", "base min", "act min", "d_min", "base pts", "act pts", "d_pts"))
groups = [("0-1 foul by half", lambda r: r["f_h1"] <= 1),
          ("exactly 2 by half", lambda r: r["f_h1"] == 2),
          ("3+ by half (TROUBLE)", lambda r: r["f_h1"] >= 3),
          ("  3rd foul in Q1", lambda r: r["t3h1"] is not None and r["t3h1"] < 600),
          ("  3rd foul in Q2", lambda r: r["t3h1"] is not None and 600 <= r["t3h1"] < 1200)]
res = {}
for lab, f in groups:
    sub = [r for r in ST if f(r)]
    if len(sub) < 10: continue
    dm = [r["mins"] - r["b_min"] for r in sub]
    dp = [r["pts"] - r["b_pts"] for r in sub]
    res[lab] = (sub, dm, dp)
    print("%-26s %5d %8.2f %8.2f %+9.2f %8.2f %8.2f %+9.2f" %
          (lab, len(sub), statistics.mean(r["b_min"] for r in sub), statistics.mean(r["mins"] for r in sub),
           statistics.mean(dm), statistics.mean(r["b_pts"] for r in sub), statistics.mean(r["pts"] for r in sub),
           statistics.mean(dp)))
tr = res["3+ by half (TROUBLE)"]; ct = res["0-1 foul by half"]
print("  TROUBLE vs 0-1-foul games: minutes %+.2f vs %+.2f  ->  net %+.2f min (t=%.2f)" %
      (statistics.mean(tr[1]), statistics.mean(ct[1]), statistics.mean(tr[1]) - statistics.mean(ct[1]),
       (statistics.mean(tr[1]) - statistics.mean(ct[1])) /
       math.sqrt(statistics.pvariance(tr[1]) / len(tr[1]) + statistics.pvariance(ct[1]) / len(ct[1]))))
print("  TROUBLE vs 0-1-foul games: points  %+.2f vs %+.2f  ->  net %+.2f pts (t=%.2f)" %
      (statistics.mean(tr[2]), statistics.mean(ct[2]), statistics.mean(tr[2]) - statistics.mean(ct[2]),
       (statistics.mean(tr[2]) - statistics.mean(ct[2])) /
       math.sqrt(statistics.pvariance(tr[2]) / len(tr[2]) + statistics.pvariance(ct[2]) / len(ct[2]))))
sub = tr[0]
print("  of the TROUBLE games, %.1f%% saw her finish under her baseline minutes; median minutes lost %.1f" %
      (100 * sum(1 for r in sub if r["mins"] < r["b_min"]) / len(sub), -statistics.median(tr[1])))
print("  she still fouled out in %.1f%% of TROUBLE games (6 fouls)" %
      (100 * sum(1 for r in sub if r["nfoul"] >= 6) / len(sub)))

print("\n=== is the drop-off 'catastrophic' for the TEAM? (in-game, unbettable, mechanism only) ===")
tg = collections.defaultdict(lambda: collections.Counter())
for r in P:
    tg[(r["gid"], r["side"])]["n"] += 1
byteam = collections.defaultdict(list)
for r in ST:
    byteam[(r["gid"], r["side"])].append(r)
der = collections.defaultdict(dict)
for r in csv.DictReader(open(os.path.join(H, "pbp_derived.csv"), encoding="utf-8")):
    der[r["game_id"]][r["side"]] = r
rowsm = load_master()
mm = {(r["game_id"], r["side"]): r for r in rowsm}
A = []
for (gid, side), lst in byteam.items():
    key = (gid, side)
    if key not in mm: continue
    g = mm[key]
    ntr = sum(1 for r in lst if r["trouble"])
    exp = sum(r["b_pts"] for r in lst)
    A.append(dict(gid=gid, side=side, ntr=ntr, pts=g["pts"], total=g["total"], gt=g["game_total"],
                  ou_o=g["ou_o"], ou_u=g["ou_u"], starpts=sum(r["pts"] for r in lst), exp=exp))
for k in (0, 1, 2):
    sub = [a for a in A if a["ntr"] == k] if k < 2 else [a for a in A if a["ntr"] >= 2]
    if len(sub) < 20: continue
    print("  %s rotation players in trouble: n=%d team-games  team pts %.2f  star pts %.2f (expected %.2f, %+.2f)" %
          (("%d" % k) if k < 2 else "2+", len(sub), statistics.mean(a["pts"] for a in sub),
           statistics.mean(a["starpts"] for a in sub), statistics.mean(a["exp"] for a in sub),
           statistics.mean(a["starpts"] - a["exp"] for a in sub)))

print("\n=== THE ONLY PRE-GAME-BETTABLE VERSION: does it predict her NEXT game? ===")
N = [r for r in ST if r["nxt"] is not None and r["nxt"].get("b_min") is not None]
print("%-26s %5s %10s %10s %10s %10s" % ("group (this game)", "n", "nxt d_min", "nxt d_pts", "nxt mins", "nxt pts"))
store = {}
for lab, f in (("0-1 foul by half", lambda r: r["f_h1"] <= 1),
               ("exactly 2 by half", lambda r: r["f_h1"] == 2),
               ("3+ by half (TROUBLE)", lambda r: r["f_h1"] >= 3)):
    sub = [r for r in N if f(r)]
    if len(sub) < 10: continue
    dm = [r["nxt"]["mins"] - r["nxt"]["b_min"] for r in sub]
    dp = [r["nxt"]["pts"] - r["nxt"]["b_pts"] for r in sub]
    store[lab] = (sub, dm, dp)
    print("%-26s %5d %+10.3f %+10.3f %10.2f %10.2f" %
          (lab, len(sub), statistics.mean(dm), statistics.mean(dp),
           statistics.mean(r["nxt"]["mins"] for r in sub), statistics.mean(r["nxt"]["pts"] for r in sub)))
a = store["3+ by half (TROUBLE)"]; b = store["0-1 foul by half"]
for i, nm in ((1, "minutes"), (2, "points")):
    t = (statistics.mean(a[i]) - statistics.mean(b[i])) / math.sqrt(
        statistics.pvariance(a[i]) / len(a[i]) + statistics.pvariance(b[i]) / len(b[i]))
    print("  NEXT-game %s: trouble %+.3f vs clean %+.3f  -> net %+.3f (t=%.2f)" %
          (nm, statistics.mean(a[i]), statistics.mean(b[i]), statistics.mean(a[i]) - statistics.mean(b[i]), t))
# player-block permutation on the next-game points effect
obs = statistics.mean(a[2]) - statistics.mean(b[2])
byp = collections.defaultdict(list)
for r in N: byp[r["player"]].append(r)
rnd = random.Random(7); nb = 0; NP = 3000
for _ in range(NP):
    lab_ = []
    for p, v in byp.items():
        fl = [r["trouble"] for r in v]
        rnd.shuffle(fl)
        for r, x in zip(v, fl): lab_.append((r, x))
    aa = [r["nxt"]["pts"] - r["nxt"]["b_pts"] for r, x in lab_ if x == 1]
    bb = [r["nxt"]["pts"] - r["nxt"]["b_pts"] for r, x in lab_ if x == 0 and r["f_h1"] <= 1]
    if aa and bb and (statistics.mean(aa) - statistics.mean(bb)) >= obs: nb += 1
print("  player-block permutation p (next-game points effect) = %.4f" % (nb / NP))
import pickle
pickle.dump([{k: v for k, v in r.items() if k != "nxt"} for r in P], open(os.path.join(H, "pbpx_c_pg.pkl"), "wb"))
print("saved pbpx_c_pg.pkl")
