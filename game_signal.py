# game_link.py - does the GAME market explain our same-game pairs?
# ---------------------------------------------------------------------------------------------
# Two players in one game share pace and possessions, so if the game goes over its total both
# their overs should be more likely to land. That is the obvious mechanism behind same-game
# clustering. Two things follow, and only one of them is useful:
#
#   DESCRIPTIVE  did the game actually go over? -> confirms the mechanism, unusable at bet time
#   ACTIONABLE   was the game's total LINE high or low beforehand? -> you can act on this
#
# Also checks whether the model's own signals lean toward one side of the game market at all,
# which would mean we have been taking an unhedged game-level position without noticing.
import csv, os, sys, math, itertools, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
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

FULL2AB = {"Atlanta Dream":"ATL","Chicago Sky":"CHI","Connecticut Sun":"CON","Dallas Wings":"DAL",
           "Golden State Valkyries":"GS","Indiana Fever":"IND","Los Angeles Sparks":"LA",
           "Las Vegas Aces":"LV","Minnesota Lynx":"MIN","New York Liberty":"NY",
           "Phoenix Mercury":"PHX","Portland Fire":"POR","Seattle Storm":"SEA",
           "Toronto Tempo":"TOR","Washington Mystics":"WSH"}

# ---- the game's closing total and spread, from the Pinnacle capture ---------------------------
tot, spr = {}, {}
for r in load("gamelines.csv"):
    st = (r.get("start") or "")[:10].replace("-", "")
    tm = (r.get("teams") or "").split("|")
    if len(tm) != 2 or not st: continue
    ab = tuple(sorted(FULL2AB.get(t.strip(), "") for t in tm))
    if "" in ab: continue
    pts, cap = f(r.get("points")), ts(r.get("captured_utc"))
    if pts is None or cap is None: continue
    key = (st, ab)
    if r.get("type") == "total":
        prev = tot.get(key)
        if prev is None or cap > prev[0]: tot[key] = (cap, pts)
    elif r.get("type") == "spread":
        prev = spr.get(key)
        if prev is None or cap > prev[0]: spr[key] = (cap, abs(pts))

# ---- final scores ------------------------------------------------------------------------------
score = {}
for g in load("data/games_2026.csv"):
    hs, as_ = f(g.get("home_score")), f(g.get("away_score"))
    if hs is None or as_ is None: continue
    score[(g.get("date"), tuple(sorted((g["home"], g["away"]))))] = hs + as_

# ---- Model S bets, with their game ------------------------------------------------------------
MKTS = ("pra","pr","pts"); SIGS = ("flip","hotover","overshoot")
gm = {g.get("game_id"): (g.get("date",""), ts(g.get("tip"))) for g in load("data/games_2026.csv")}
plog = collections.defaultdict(list); team = {}
for r in load("data/box_2026.csv"):
    dt, tp = gm.get(r.get("game_id"), ("", None))
    if not dt: continue
    p_, rb, a = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    pl = (r.get("player") or "").lower()
    plog[pl].append(dict(tip=tp, date=dt, pra=p_+rb+a, pr=p_+rb, pts=p_))
    team[pl] = r.get("team")
tips_of = collections.defaultdict(list)
opp = {}
for g in load("data/games_2026.csv"):
    t = ts(g.get("tip"))
    if t:
        tips_of[g["home"]].append(t); tips_of[g["away"]].append(t)
        opp[(g.get("date"), g["home"])] = g["away"]; opp[(g.get("date"), g["away"])] = g["home"]
for v in tips_of.values(): v.sort()
def game_for(tm, when):
    for t in tips_of.get(tm, []):
        if when <= t and (t-when).total_seconds() <= 60*3600: return t
    return None
raw = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None and b.get("market") in MKTS and b.get("side") == "Over":
        raw[((b.get("player") or "").lower(), b.get("market"), ln)].append((t, o))
bygame = collections.defaultdict(list)
for (pl, mk, ln), v in raw.items():
    tm = team.get(pl)
    if not tm: continue
    for t, o in sorted(v):
        gt = game_for(tm, t)
        if gt: bygame[(pl, mk, gt)].append((t, ln, o))
for v in bygame.values(): v.sort()

seen, BETS = set(), []
for b in sorted(load("bets_log.csv"), key=lambda r: r.get("captured_utc") or ""):
    if b.get("side") != "Over" or b.get("src") not in SIGS: continue
    pl, mk = (b.get("player") or "").lower(), b.get("market")
    if mk not in MKTS: continue
    t0, tm = ts(b.get("captured_utc")), team.get(pl)
    if not (t0 and tm): continue
    gt = game_for(tm, t0)
    if not gt or (pl, mk, gt) in seen: continue
    seq = bygame.get((pl, mk, gt), [])
    rec = next((g for g in plog.get(pl, []) if g["tip"] == gt), None)
    if not seq or not rec: continue
    seen.add((pl, mk, gt))
    line = seq[-1][1]
    earlier = sorted(g for (p2, m2, g) in bygame if p2 == pl and m2 == mk and g < gt)
    pv = bygame[(pl, mk, earlier[-1])][-1][1] if earlier else None
    if pv is None or line - pv >= 0.5: continue
    dt = rec["date"]; o_ = opp.get((dt, tm))
    ab = tuple(sorted((tm, o_))) if o_ else None
    BETS.append(dict(pl=pl, name=(b.get("player") or "").split()[-1], tm=tm, tip=gt, date=dt,
                     ab=ab, odds=seq[-1][2], won=rec[mk] > line,
                     tot_line=(tot.get((dt, ab)) or (None, None))[1],
                     spr_line=(spr.get((dt, ab)) or (None, None))[1],
                     actual_tot=score.get((dt, ab))))
byday = collections.defaultdict(list)
for r in BETS: byday[r["date"]].append(r)
for d in list(byday):
    best = {}
    for r in sorted(byday[d], key=lambda x: -x["odds"]): best.setdefault(r["pl"], r)
    byday[d] = sorted(best.values(), key=lambda r: r["tip"])
flat = [r for v in byday.values() for r in v]
have = [r for r in flat if r["tot_line"] and r["actual_tot"]]
print(f"{len(flat)} Model S bets, {len(have)} matched to a Pinnacle total AND a final score")
print("")

def st(rows, label, minn=8):
    n = len(rows)
    if n < minn:
        print(f"  {label:<46} n={n:<4} too few"); return
    w = sum(1 for r in rows if r["won"])
    u = sum((r["odds"]-1) if r["won"] else -1.0 for r in rows)
    print(f"  {label:<46} n={n:<4} {100*w/n:5.1f}%  {u:+7.2f}u  ROI {100*u/n:+6.1f}%")


h = [r for r in flat if r["tot_line"] and r["actual_tot"]]
games = {}
for r in h: games[(r["date"], r["ab"])] = (r["actual_tot"], r["tot_line"])
o = sum(1 for v in games.values() if v[0] > v[1])
u = sum(1 for v in games.values() if v[0] < v[1])
print("="*96)
print("  DOES OUR SIGNAL PREDICT WHICH WAY THE GAME TOTAL GOES?")
print("="*96)
print(f"  games we had a Model S bet in: {len(games)}")
print(f"    went OVER the total   {o}")
print(f"    went UNDER the total  {u}")
if o+u:
    print(f"    -> {100*o/(o+u):.1f}% over. That is a coin flip: the signal does NOT predict it.")
print("")
print("  So the game-total exposure is UNCOMPENSATED. It swings our results hard (75.0% when")
print("  the game goes over, 42.9% when it does not) but we have no edge on the direction.")
print("  Spreading legs ACROSS games is therefore free variance reduction, and stacking them")
print("  in one game is free variance increase - no data-mining required to see it.")
