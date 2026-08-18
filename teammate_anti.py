# teammate_anti.py - when our model likes player A, does her TEAMMATE underperform?
# ---------------------------------------------------------------------------------------------
# The user's idea, and it has a real mechanism behind it: a team has a fixed number of
# possessions and shots. If Ogunbowale takes 20 of them, someone else is not taking them. So an
# A-over ought to imply a B-under, and the book may not move B's number to reflect it.
#
# BUT there is a competing mechanism pulling the other way, and I already measured it: same-game
# pairs both went OVER 45.5% of the time against 38.6% under independence. Game PACE lifts every
# player at once. So the question is which force wins - usage competition (negative) or pace
# (positive).
#
# Also tests the second half of the question: does the BOOK reveal it? If it is cutting the
# teammate's number while holding ours, that is the book redistributing expectation, and it
# would be visible before tip.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260908)
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

ALL_MK = ("pts", "pra", "pr", "pa", "reb", "ast", "ra")
BET_MK = ("pra", "pr", "pts")
SIGS = ("flip", "hotover", "overshoot")
gmeta = {}
for g in load("data/games_2026.csv"):
    t = ts(g.get("tip"))
    if t: gmeta[g.get("game_id")] = (g.get("date", ""), t)
pgrow = {}; teamof = {}
for r in load("data/box_2026.csv"):
    gid = r.get("game_id")
    if gid not in gmeta: continue
    dt, tp = gmeta[gid]
    pl, tm = (r.get("player") or "").lower(), r.get("team")
    p_, rb, a = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    pgrow[(pl, tp)] = dict(tm=tm, date=dt, pts=p_, reb=rb, ast=a,
                           pra=p_+rb+a, pr=p_+rb, pa=p_+a, ra=rb+a)
    teamof[pl] = tm
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
    if t and o and ln is not None and b.get("market") in ALL_MK:
        raw[((b.get("player") or "").lower(), b.get("market"), b.get("side"), ln)].append((t, o))
bygame = collections.defaultdict(list)
for (pl, mk, sd, ln), v in raw.items():
    tm = teamof.get(pl)
    if not tm: continue
    for t, o in sorted(v):
        g2 = game_for(tm, t)
        if g2: bygame[(pl, mk, sd, g2)].append((t, ln, o))
for v in bygame.values(): v.sort()

# our starred bets
seen, OURS = set(), []
for b in sorted(load("bets_log.csv"), key=lambda r: r.get("captured_utc") or ""):
    if b.get("side") != "Over" or b.get("src") not in SIGS: continue
    pl, mk = (b.get("player") or "").lower(), b.get("market")
    if mk not in BET_MK: continue
    t0, tm = ts(b.get("captured_utc")), teamof.get(pl)
    if not (t0 and tm): continue
    gt = game_for(tm, t0)
    if not gt or (pl, mk, gt) in seen: continue
    seq = bygame.get((pl, mk, "Over", gt), [])
    now = pgrow.get((pl, gt))
    if not seq or not now: continue
    line = seq[-1][1]
    earlier = sorted(g for (p2, m2, s2, g) in bygame
                     if p2 == pl and m2 == mk and s2 == "Over" and g < gt)
    pv = bygame[(pl, mk, "Over", earlier[-1])][-1][1] if earlier else None
    if pv is None or line - pv >= 0.5: continue
    seen.add((pl, mk, gt))
    OURS.append(dict(pl=pl, tm=tm, gt=gt, date=now["date"], mk=mk, line=line))

def prev_line(pl, mk, sd, gt):
    e = sorted(g for (p2, m2, s2, g) in bygame if p2 == pl and m2 == mk and s2 == sd and g < gt)
    return bygame[(pl, mk, sd, e[-1])][-1][1] if e else None

# every TEAMMATE quote on the same game
MATES = []
for o in OURS:
    for (pl, mk, sd, gt), seq in bygame.items():
        if gt != o["gt"] or pl == o["pl"] or sd != "Over": continue
        if teamof.get(pl) != o["tm"] or mk not in BET_MK: continue
        now = pgrow.get((pl, gt))
        if not now or now[mk] == seq[-1][1]: continue
        line, price = seq[-1][1], seq[-1][2]
        pv = prev_line(pl, mk, "Over", gt)
        MATES.append(dict(mate=pl, of=o["pl"], mk=mk, date=o["date"], line=line, odds=price,
                          over_won=now[mk] > line,
                          mv=(None if pv is None else line - pv)))
print(f"{len(OURS)} starred Model S bets")
print(f"{len(MATES)} teammate over-quotes on those same games")
print("")

# baseline: EVERY over on the board, so we know what 'normal' looks like
BASE = []
for (pl, mk, sd, gt), seq in bygame.items():
    if sd != "Over" or mk not in BET_MK: continue
    now = pgrow.get((pl, gt))
    if not now or now[mk] == seq[-1][1]: continue
    BASE.append(dict(over_won=now[mk] > seq[-1][1], odds=seq[-1][2]))
def roi(rows, key="over_won"):
    return sum((r["odds"]-1) if r[key] else -1.0 for r in rows)/len(rows) if rows else 0.0
def show(rows, label, key="over_won", minn=25):
    n = len(rows)
    if n < minn:
        print(f"  {label:<48} n={n:<5} too few"); return
    w = sum(1 for r in rows if r[key])
    print(f"  {label:<48} n={n:<5} over hit {100*w/n:5.1f}%  ROI {100*roi(rows,key):+6.1f}%")

print("="*104)
print("  1. DO TEAMMATES OF OUR PICKS UNDERPERFORM?")
print("="*104)
show(BASE, "EVERY over on the board (the baseline)")
show(MATES, "teammates of a Model S pick, their OVER")
print("")
print("  and the UNDER on those same teammates, which is what the theory says to buy:")
mu = [dict(r, und=not r["over_won"]) for r in MATES]
n = len(mu); w = sum(1 for r in mu if r["und"])
print(f"  {'teammate UNDER (at the over price, indicative)':<48} n={n:<5} "
      f"under hit {100*w/n:5.1f}%")
print("")
print("="*104)
print("  2. DOES THE BOOK REVEAL IT? teammate's line vs HER previous game")
print("="*104)
have = [r for r in MATES if r["mv"] is not None]
print(f"  {len(have)} teammate quotes have a previous line")
show([r for r in have if r["mv"] <= -0.5], "  book CUT the teammate's number")
show([r for r in have if abs(r["mv"]) < 0.5], "  teammate's number held")
show([r for r in have if r["mv"] >= 0.5],  "  book RAISED the teammate's number")
print("")
print("  the theory says: our pick soaks up the usage, so a teammate whose number the book has")
print("  CUT should be the one to fade. Compare that row against the baseline above.")
print("")
print("="*104)
print("  3. THE COMPETING FORCE - pace. Did BOTH go over on the same game?")
print("="*104)
pair = collections.defaultdict(lambda: [None, []])
for o in OURS:
    now = pgrow.get((o["pl"], o["gt"]))
    if now: pair[(o["date"], o["pl"])][0] = now[o["mk"]] > o["line"]
for m in MATES:
    pair[(m["date"], m["of"])][1].append(m["over_won"])
both = [v for v in pair.values() if v[0] is not None and v[1]]
ourw = sum(1 for v in both if v[0])
mate_when_we_won = [x for v in both if v[0] for x in v[1]]
mate_when_we_lost = [x for v in both if not v[0] for x in v[1]]
print(f"  games where OUR pick went over:   {ourw} of {len(both)}")
if mate_when_we_won:
    print(f"    teammates' overs on those nights   {100*sum(mate_when_we_won)/len(mate_when_we_won):5.1f}% "
          f"(n={len(mate_when_we_won)})")
if mate_when_we_lost:
    print(f"    teammates' overs when ours LOST    {100*sum(mate_when_we_lost)/len(mate_when_we_lost):5.1f}% "
          f"(n={len(mate_when_we_lost)})")
print("")
print("  if usage competition dominated, teammates would do WORSE when our pick goes over.")
print("  if pace dominates, they do BETTER. the two rows above decide it.")
