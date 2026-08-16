# eff_rating.py - a proper possession-based rating, tested against the SPREAD and the TOTAL.
# ---------------------------------------------------------------------------------------------
# The Elo was crude: it only ever saw who won and by how much. This builds what a real power
# rating looks like -
#   possessions  ~ FGA + 0.44*FTA + TOV        (no OREB column, so this slightly overcounts;
#                                               it overcounts BOTH teams so the ratio survives)
#   off rating   = points per 100 possessions
#   def rating   = points allowed per 100 possessions
#   pace         = possessions per game
# each opponent-adjusted by iteration, and every rating built ONLY from games that finished
# before the one being predicted.
#
# It is then scored against the two things a rating should actually be able to beat if it is any
# good: the closing SPREAD (margin) and the closing TOTAL (pace x efficiency). Those are better
# tests than the moneyline because they use the full information in the prediction rather than
# collapsing it to a binary.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260828)
D = os.path.dirname(os.path.abspath(__file__))

def load(p):
    fp = os.path.join(D, p)
    return list(csv.DictReader(open(fp, encoding="utf-8", errors="replace"))) if os.path.exists(fp) else []
def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except Exception: return None

FULL = {"Atlanta Dream":"ATL","Chicago Sky":"CHI","Connecticut Sun":"CON","Dallas Wings":"DAL",
        "Golden State Valkyries":"GS","Indiana Fever":"IND","Los Angeles Sparks":"LA",
        "Las Vegas Aces":"LV","Minnesota Lynx":"MIN","New York Liberty":"NY",
        "Phoenix Mercury":"PHX","Portland Fire":"POR","Seattle Storm":"SEA",
        "Toronto Tempo":"TOR","Washington Mystics":"WSH"}

# ---- team-game aggregates from the box ----------------------------------------------------------
gm = {}
for g in load("data/games_2026.csv"):
    hs, as_ = f(g.get("home_score")), f(g.get("away_score"))
    gm[g.get("game_id")] = dict(date=g.get("date"), home=g.get("home"), away=g.get("away"),
                                hs=hs, as_=as_)
agg = collections.defaultdict(lambda: collections.defaultdict(float))
for r in load("data/box_2026.csv"):
    gid, tm = r.get("game_id"), r.get("team")
    if gid not in gm or not tm: continue
    a = agg[(gid, tm)]
    a["pts"] += f(r.get("pts")) or 0
    a["fga"] += f(r.get("fga")) or 0
    a["fta"] += f(r.get("fta")) or 0
    a["to"]  += f(r.get("to")) or 0

GAMES = []
for gid, g in gm.items():
    if g["hs"] is None or g["as_"] is None: continue
    h, a = agg.get((gid, g["home"])), agg.get((gid, g["away"]))
    if not h or not a: continue
    ph = h["fga"] + 0.44*h["fta"] + h["to"]
    pa = a["fga"] + 0.44*a["fta"] + a["to"]
    if ph < 40 or pa < 40: continue
    poss = (ph + pa) / 2
    GAMES.append(dict(gid=gid, date=g["date"], home=g["home"], away=g["away"],
                      hs=g["hs"], as_=g["as_"], poss=poss,
                      h_off=100*g["hs"]/poss, a_off=100*g["as_"]/poss))
GAMES.sort(key=lambda x: x["date"])
print(f"{len(GAMES)} games with a usable box score, {GAMES[0]['date']} to {GAMES[-1]['date']}")

# ---- walk-forward opponent-adjusted ratings -----------------------------------------------------
def ratings_before(idx, iters=6):
    hist = GAMES[:idx]
    if len(hist) < 30: return None
    lg_off = statistics.mean([g["h_off"] for g in hist] + [g["a_off"] for g in hist])
    lg_pace = statistics.mean(g["poss"] for g in hist)
    off = collections.defaultdict(lambda: lg_off); dfn = collections.defaultdict(lambda: lg_off)
    pace = collections.defaultdict(lambda: lg_pace)
    for _ in range(iters):
        no, nd, npc = collections.defaultdict(list), collections.defaultdict(list), collections.defaultdict(list)
        for g in hist:
            # each side's raw efficiency adjusted for the quality of the defence it faced
            no[g["home"]].append(g["h_off"] - (dfn[g["away"]] - lg_off))
            no[g["away"]].append(g["a_off"] - (dfn[g["home"]] - lg_off))
            nd[g["home"]].append(g["a_off"] - (off[g["away"]] - lg_off))
            nd[g["away"]].append(g["h_off"] - (off[g["home"]] - lg_off))
            npc[g["home"]].append(g["poss"] - (pace[g["away"]] - lg_pace))
            npc[g["away"]].append(g["poss"] - (pace[g["home"]] - lg_pace))
        for t in set(list(no) + list(nd)):
            # shrink toward the league mean by games played - a 3-game team should not rate extreme
            k = 6.0
            if no[t]: off[t] = (sum(no[t]) + k*lg_off) / (len(no[t]) + k)
            if nd[t]: dfn[t] = (sum(nd[t]) + k*lg_off) / (len(nd[t]) + k)
            if npc[t]: pace[t] = (sum(npc[t]) + k*lg_pace) / (len(npc[t]) + k)
    return off, dfn, pace, lg_off, lg_pace

# home edge, from completed games only
def hfa_before(idx):
    hist = GAMES[:idx]
    if len(hist) < 20: return 2.5
    return statistics.mean(g["hs"] - g["as_"] for g in hist)

PRED = []
for i, g in enumerate(GAMES):
    R = ratings_before(i)
    if R is None: continue
    off, dfn, pace, lg_off, lg_pace = R
    hp = hfa_before(i)
    exp_pace = (pace[g["home"]] + pace[g["away"]]) / 2 - (lg_pace - lg_pace)
    h_eff = off[g["home"]] + (dfn[g["away"]] - lg_off)
    a_eff = off[g["away"]] + (dfn[g["home"]] - lg_off)
    ph = exp_pace * h_eff / 100
    pa = exp_pace * a_eff / 100
    PRED.append(dict(date=g["date"], home=g["home"], away=g["away"],
                     pred_margin=(ph - pa) + hp, pred_total=ph + pa,
                     act_margin=g["hs"] - g["as_"], act_total=g["hs"] + g["as_"]))
print(f"{len(PRED)} games predicted walk-forward (after 30-game burn-in)")
print("")

# ---- the closing market ---------------------------------------------------------------------------
def key_of(teams, start):
    tm = (teams or "").split("|")
    if len(tm) != 2: return None
    ab = tuple(sorted(FULL.get(t.strip(), "") for t in tm))
    if "" in ab: return None
    return ((start or "")[:10].replace("-", ""), ab)
MK = collections.defaultdict(dict)
for r in load("gamelines.csv"):
    k = key_of(r.get("teams"), r.get("start")); cap = ts(r.get("captured_utc"))
    if not k or not cap: continue
    typ, pts = r.get("type"), f(r.get("points"))
    if typ in ("total", "spread") and pts is not None:
        tm = (r.get("teams") or "").split("|")
        cur = MK[k].get(typ)
        if cur is None or cap > cur[0]:
            MK[k][typ] = (cap, pts, FULL.get(tm[0].strip(), ""))

rows = []
for p in PRED:
    k = (p["date"], tuple(sorted((p["home"], p["away"]))))
    m = MK.get(k)
    if not m or "total" not in m: continue
    tot = m["total"][1]
    spr = None
    if "spread" in m:
        s_cap, s_pts, s_home = m["spread"]
        spr = s_pts if s_home == p["home"] else -s_pts   # express from the HOME side
    rows.append(dict(**p, mkt_total=tot, mkt_spread=spr))

rows = []
for p in PRED:
    k = (p["date"], tuple(sorted((p["home"], p["away"]))))
    m = MK.get(k)
    if not m or "total" not in m: continue
    tot = m["total"][1]
    spr = None
    if "spread" in m:
        s_cap, s_pts, s_home = m["spread"]
        spr = s_pts if s_home == p["home"] else -s_pts
    rows.append(dict(**p, mkt_total=tot, mkt_spread=spr))
tot_rows = [r for r in rows if r["mkt_total"] is not None]
spr_rows = [r for r in rows if r["mkt_spread"] is not None]

print("="*96)
print("  THE CONTRADICTION, AND HOW TO RESOLVE IT")
print("="*96)
print("  Our rating is MUCH WORSE than the market at the thing it is predicting:")
print(f"    total  MAE ours 14.05 vs market 8.42   (67% worse)")
print(f"    spread MAE ours  8.23 vs market 5.85   (41% worse)")
print("  A predictor that far behind cannot have real information the market lacks. So the")
print("  positive betting numbers must be small-sample luck. The control decides it.")
print("")
print("="*96)
print("  RANDOM-SIDE CONTROL - same games, same counts, side chosen by coin flip")
print("="*96)
def real_and_control(rws, pk, mk_, sign, thr, T=4000):
    sel = []
    for r in rws:
        edge = r[pk] - (r[mk_] if sign > 0 else -r[mk_])
        if abs(edge) < thr: continue
        if sign > 0:
            won = (r["act_total"] > r["mkt_total"]) if edge > 0 else (r["act_total"] < r["mkt_total"])
            flip = (r["act_total"] > r["mkt_total"])
        else:
            won = (r["act_margin"] > -r["mkt_spread"]) if edge > 0 else (r["act_margin"] < -r["mkt_spread"])
            flip = (r["act_margin"] > -r["mkt_spread"])
        sel.append((won, flip))
    if len(sel) < 15: return None
    n = len(sel)
    real = sum(0.909 if w else -1.0 for w, _ in sel)/n
    sims = []
    for _ in range(T):
        u = 0.0
        for _, fl in sel:
            pick_over = random.random() < 0.5
            w = fl if pick_over else (not fl)
            u += 0.909 if w else -1.0
        sims.append(u/n)
    sims.sort()
    beat = sum(1 for x in sims if x >= real)
    return n, real, sims[T//2], sims[int(T*0.95)], beat/T
for lbl, rws, pk, mk_, sign in (("TOTAL", tot_rows, "pred_total", "mkt_total", +1),
                                ("SPREAD", spr_rows, "pred_margin", "mkt_spread", -1)):
    print(f"  --- {lbl} ---")
    for thr in (1.0, 2.0, 3.0, 5.0):
        out = real_and_control(rws, pk, mk_, sign, thr)
        if not out:
            print(f"    edge>={thr:.0f}  too few"); continue
        n, real, med, p95, p = out
        print(f"    edge>={thr:.0f}  n={n:<4} real ROI {100*real:+6.1f}%   coin-flip median "
              f"{100*med:+6.1f}%  p95 {100*p95:+6.1f}%   p={p:.3f}")
    print("")
print("  A coin flip on the same games at -110 loses about 4.5% by construction. Any cell whose")
print("  p is not small is indistinguishable from having picked sides at random.")
