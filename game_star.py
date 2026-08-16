# game_star.py - the STAR logic, applied to the GAME markets instead of the player prop.
# ---------------------------------------------------------------------------------------------
# The user's idea, and it is the right shape. The star works because it compares tonight's number
# to her PREVIOUS GAME's number - a between-games re-evaluation. Everything I have tested on the
# game markets so far used the ABSOLUTE level (is the total high?) or INTRADAY movement (did it
# drift today?), and both came back empty at global p=0.91.
#
# This asks the untested question: is tonight's game total HIGHER or LOWER than the total for
# this team's PREVIOUS game? Same for the spread and the moneyline. If the book has raised the
# team's expected pace since last time, that is a re-pricing of exactly the kind the player-level
# star detects - and it should show up in our overs.
#
# Pre-registered: 3 markets x {higher, lower, unchanged} + a magnitude split, then a global
# permutation over the whole grid. Coverage is the binding constraint and is printed first.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260825)
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
def am(p):
    v = f(p)
    if v is None: return None
    return (-v)/((-v)+100) if v < 0 else 100/(v+100)

FULL2AB = {"Atlanta Dream":"ATL","Chicago Sky":"CHI","Connecticut Sun":"CON","Dallas Wings":"DAL",
           "Golden State Valkyries":"GS","Indiana Fever":"IND","Los Angeles Sparks":"LA",
           "Las Vegas Aces":"LV","Minnesota Lynx":"MIN","New York Liberty":"NY",
           "Phoenix Mercury":"PHX","Portland Fire":"POR","Seattle Storm":"SEA",
           "Toronto Tempo":"TOR","Washington Mystics":"WSH"}

# ---- closing game markets, per (date, team-pair), plus which side is home ----------------------
G = collections.defaultdict(dict)
for r in load("gamelines.csv"):
    st = (r.get("start") or "")[:10].replace("-", "")
    tm = (r.get("teams") or "").split("|")
    if len(tm) != 2 or not st: continue
    hm, aw = FULL2AB.get(tm[0].strip(), ""), FULL2AB.get(tm[1].strip(), "")
    if not hm or not aw: continue
    ab = tuple(sorted((hm, aw)))
    cap, pts = ts(r.get("captured_utc")), f(r.get("points"))
    if cap is None: continue
    slot = G[(st, ab)]
    slot["home"] = hm
    if r.get("type") == "total" and pts is not None:
        if "tot" not in slot or cap > slot["tot"][0]: slot["tot"] = (cap, pts)
    elif r.get("type") == "spread" and pts is not None:
        if "spr" not in slot or cap > slot["spr"][0]: slot["spr"] = (cap, pts)
    elif r.get("type") == "moneyline":
        pr = (r.get("prices") or "").split(",")
        h = am(pr[0]) if pr and pr[0] else None
        if h is not None and ("ml" not in slot or cap > slot["ml"][0]): slot["ml"] = (cap, h)

# per TEAM, its game-market history in date order, from that team's own point of view
hist = collections.defaultdict(list)
for (st, ab), slot in G.items():
    hm = slot.get("home")
    if not hm: continue
    for t in ab:
        own_home = (t == hm)
        spr = slot.get("spr", (None, None))[1]
        ml = slot.get("ml", (None, None))[1]
        hist[t].append(dict(date=st, tot=slot.get("tot", (None, None))[1],
                            # spread and ml expressed from THIS team's side, else the sign is meaningless
                            spr=(spr if own_home else (None if spr is None else -spr)),
                            ml=(ml if own_home else (None if ml is None else 1-ml))))
for v in hist.values(): v.sort(key=lambda x: x["date"])

def prev_game(team, date):
    v = [x for x in hist.get(team, []) if x["date"] < date]
    return v[-1] if v else None
def this_game(team, date):
    return next((x for x in hist.get(team, []) if x["date"] == date), None)

# ---- Model S bets -------------------------------------------------------------------------------
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
for g in load("data/games_2026.csv"):
    t = ts(g.get("tip"))
    if t: tips_of[g["home"]].append(t); tips_of[g["away"]].append(t)
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
        g2 = game_for(tm, t)
        if g2: bygame[(pl, mk, g2)].append((t, ln, o))
for v in bygame.values(): v.sort()

seen, K = set(), []
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
    now_, prv = this_game(tm, rec["date"]), prev_game(tm, rec["date"])
    d = {}
    if now_ and prv:
        for k in ("tot", "spr", "ml"):
            d[k] = (now_[k] - prv[k]) if (now_[k] is not None and prv[k] is not None) else None
    K.append(dict(pl=pl, tm=tm, date=rec["date"], odds=seq[-1][2], won=rec[mk] > line,
                  d_tot=d.get("tot"), d_spr=d.get("spr"), d_ml=d.get("ml")))
byday = collections.defaultdict(list)
for r in K: byday[r["date"]].append(r)
for dd in list(byday):
    best = {}
    for r in sorted(byday[dd], key=lambda x: -x["odds"]): best.setdefault(r["pl"], r)
    byday[dd] = list(best.values())
K = [r for v in byday.values() for r in v]

print(f"{len(K)} Model S bets. COVERAGE - needs this game AND the team's previous game priced:")
for k, lbl in (("d_tot","total"), ("d_spr","spread (own side)"), ("d_ml","moneyline (own win prob)")):
    print(f"    {lbl:<26} {sum(1 for r in K if r.get(k) is not None):>4} of {len(K)}")
print("")
def roi(rows): return sum((r["odds"]-1) if r["won"] else -1.0 for r in rows)/len(rows) if rows else 0.0
def show(rows, label, minn=12):
    n = len(rows)
    if n < minn:
        print(f"  {label:<44} n={n:<4} too few"); return
    w = sum(1 for r in rows if r["won"])
    print(f"  {label:<44} n={n:<4} {100*w/n:5.1f}%  ROI {100*roi(rows):+6.1f}%")

CELLS = []
print("="*100)
print("  IS TONIGHT'S GAME NUMBER HIGHER OR LOWER THAN THIS TEAM'S LAST GAME?")
print("="*100)
SPECS = [("TOTAL", "d_tot", 2.0), ("SPREAD (own side)", "d_spr", 1.5), ("MONEYLINE (own p)", "d_ml", 0.05)]
for lbl, key, big in SPECS:
    print(f"  --- {lbl} ---")
    have = [r for r in K if r.get(key) is not None]
    if len(have) < 20:
        print(f"    only {len(have)} priced - skipping\n"); continue
    # BIND key AND big AS DEFAULTS. Without this the lambdas capture the loop variables by
    # reference, so after the loop every stored cell evaluates against the LAST spec (d_ml).
    # The on-screen table was right - it is evaluated inside the iteration - but CELLS was not,
    # so the permutation test was scoring twelve moneyline cells under three different labels.
    for sub, sel in ((f"HIGHER than last game", lambda r, k=key: r[k] > 0),
                     (f"LOWER than last game",  lambda r, k=key: r[k] < 0),
                     (f"unchanged",             lambda r, k=key: r[k] == 0),
                     (f"HIGHER by {big}+",      lambda r, k=key, b=big: r[k] >= b),
                     (f"LOWER by {big}+",       lambda r, k=key, b=big: r[k] <= -b)):
        g = [r for r in have if sel(r)]
        show(g, f"    {sub}")
        if len(g) >= 12: CELLS.append((f"{lbl} {sub}", key, sel))
    print("")
if not CELLS:
    print("  nothing reached n=12 - the gameline capture is too young for this test"); raise SystemExit

def best_of(labels):
    b = -9e9; bl = ""
    for nm, key, sel in CELLS:
        g = [r for r in K if r.get(key) is not None and sel(r)]
        if len(g) < 12: continue
        v = sum((r["odds"]-1) if labels[id(r)] else -1.0 for r in g)/len(g)
        if v > b: b, bl = v, nm
    return b, bl
real, rlbl = best_of({id(r): r["won"] for r in K})
print("="*100)
print(f"  BEST CELL: {rlbl}  ROI {100*real:+.1f}%   (all {len(K)} bets: {100*roi(K):+.1f}%)")
print(f"  {len(CELLS)} cells were tested. GLOBAL permutation, 2000 shuffles:")
print("="*100)
outs = [r["won"] for r in K]
beat = 0; T = 2000; sims = []
for _ in range(T):
    sh = outs[:]; random.shuffle(sh)
    b, _ = best_of({id(r): w for r, w in zip(K, sh)})
    sims.append(b)
    if b >= real: beat += 1
sims.sort()
print(f"    shuffled best-of-grid: median {100*sims[T//2]:+.1f}%  p95 {100*sims[int(T*0.95)]:+.1f}%"
      f"  max {100*sims[-1]:+.1f}%")
print(f"    beat ours {beat}/{T}  ->  GLOBAL p = {beat/T:.4f}")
