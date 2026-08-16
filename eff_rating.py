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
print("=" * 96)
print("  CAN THE RATING BEAT THE CLOSING NUMBER?")
print("=" * 96)
print(f"  {len(rows)} predicted games also have a closing line")
if len(rows) < 25:
    print("  too few to say anything - gameline capture starts 2026-07-11"); raise SystemExit

def mae(rows, pk, ak): return sum(abs(r[pk]-r[ak]) for r in rows)/len(rows)
tot_rows = [r for r in rows if r["mkt_total"] is not None]
print("")
print(f"  TOTAL   our mean abs error {mae(tot_rows,'pred_total','act_total'):6.2f} pts")
print(f"          market mean abs error {mae([dict(r, m=r['mkt_total']) for r in tot_rows],'m','act_total'):6.2f} pts")
spr_rows = [r for r in rows if r["mkt_spread"] is not None]
if spr_rows:
    print(f"  SPREAD  our mean abs error {mae(spr_rows,'pred_margin','act_margin'):6.2f} pts")
    print(f"          market mean abs error "
          f"{sum(abs(-r['mkt_spread']-r['act_margin']) for r in spr_rows)/len(spr_rows):6.2f} pts")
print("")
print("  BETTING THE DISAGREEMENT (flat 1u at -110 = 1.909, the standard game-line price)")
print("")
for lbl, rws, pk, mk_, sign in (("TOTAL over/under", tot_rows, "pred_total", "mkt_total", +1),
                                ("SPREAD", spr_rows, "pred_margin", "mkt_spread", -1)):
    if len(rws) < 25: continue
    print(f"  --- {lbl} ---")
    for thr in (1.0, 2.0, 3.0, 5.0):
        n = w = 0; u = 0.0
        for r in rws:
            edge = r[pk] - (r[mk_] if sign > 0 else -r[mk_])
            if abs(edge) < thr: continue
            n += 1
            if sign > 0:
                won = (r["act_total"] > r["mkt_total"]) if edge > 0 else (r["act_total"] < r["mkt_total"])
            else:
                won = (r["act_margin"] > -r["mkt_spread"]) if edge > 0 else (r["act_margin"] < -r["mkt_spread"])
            w += won; u += 0.909 if won else -1.0
        if n < 15:
            print(f"    edge >= {thr:.0f} pts   n={n} too few"); continue
        print(f"    edge >= {thr:.0f} pts   n={n:<4} {100*w/n:5.1f}%  {u:+6.2f}u  ROI {100*u/n:+6.1f}%"
              f"   (break-even 52.4%)")
    print("")
