# assist_signal.py - can the assist correlation become a STANDALONE bet?
# ---------------------------------------------------------------------------------------------
# The correlation is real: teammates' assists run +0.27 above their own average on nights our
# pick hits, with the minutes confound excluded. But it was not bettable, because it was
# conditioned on our pick HITTING, which we only learn afterwards.
#
# The version that IS bettable drops the condition entirely: when Model S flags a scorer at all,
# back a teammate's ASSIST over. That needs no knowledge of the outcome - the signal is simply
# "this team is set up for a big scoring night, and somebody has to be credited with feeding it".
#
# Tested against the right baseline: every assist over on the board, not against 50%. And split
# by whether the teammate is the team's PRIMARY playmaker, since she is the one who would
# actually collect those assists.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260910)
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

BET_MK = ("pra", "pr", "pts"); SIGS = ("flip", "hotover", "overshoot")
gmeta = {}
for g in load("data/games_2026.csv"):
    t = ts(g.get("tip"))
    if t: gmeta[g.get("game_id")] = (g.get("date", ""), t)
pgrow = {}; roster = collections.defaultdict(set); teamof = {}
for r in load("data/box_2026.csv"):
    gid = r.get("game_id")
    if gid not in gmeta: continue
    dt, tp = gmeta[gid]
    pl, tm = (r.get("player") or "").lower(), r.get("team")
    p_, rb, a = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    pgrow[(pl, tp)] = dict(tm=tm, tip=tp, date=dt, min=f(r.get("min")) or 0,
                           pts=p_, reb=rb, ast=a, pra=p_+rb+a, pr=p_+rb, pa=p_+a, ra=rb+a)
    roster[(tm, tp)].add(pl); teamof[pl] = tm
hist = collections.defaultdict(list)
for (pl, tp), row in pgrow.items(): hist[pl].append(row)
for v in hist.values(): v.sort(key=lambda x: x["tip"])

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
    if t and o and ln is not None and b.get("side") == "Over":
        raw[((b.get("player") or "").lower(), b.get("market"), ln)].append((t, o))
bygame = collections.defaultdict(list)
for (pl, mk, ln), v in raw.items():
    tm = teamof.get(pl)
    if not tm: continue
    for t, o in sorted(v):
        g2 = game_for(tm, t)
        if g2: bygame[(pl, mk, g2)].append((t, ln, o))
for v in bygame.values(): v.sort()

# which games did Model S flag someone on?
flagged = set()          # (team, gametip)
seen = set()
for b in sorted(load("bets_log.csv"), key=lambda r: r.get("captured_utc") or ""):
    if b.get("side") != "Over" or b.get("src") not in SIGS: continue
    pl, mk = (b.get("player") or "").lower(), b.get("market")
    if mk not in BET_MK: continue
    t0, tm = ts(b.get("captured_utc")), teamof.get(pl)
    if not (t0 and tm): continue
    gt = game_for(tm, t0)
    if not gt or (pl, mk, gt) in seen: continue
    seq = bygame.get((pl, mk, gt), []); now = pgrow.get((pl, gt))
    if not seq or not now: continue
    line = seq[-1][1]
    e = sorted(g for (p2, m2, g) in bygame if p2 == pl and m2 == mk and g < gt)
    pv = bygame[(pl, mk, e[-1])][-1][1] if e else None
    if pv is None or line - pv >= 0.5: continue
    seen.add((pl, mk, gt))
    flagged.add((tm, gt, pl))

flag_games = {(tm, gt) for tm, gt, _ in flagged}
flag_players = {(pl, gt) for _, gt, pl in flagged}

# EVERY assist over on the board, tagged by whether a teammate was flagged
A = []
for (pl, mk, gt), seq in bygame.items():
    if mk != "ast": continue
    now = pgrow.get((pl, gt))
    if not now or now["min"] < 8: continue
    line, price = seq[-1][1], seq[-1][2]
    if now["ast"] == line: continue
    prior = [x for x in hist.get(pl, []) if x["tip"] < gt][-6:]
    if len(prior) < 4: continue
    tm = now["tm"]
    # is she the team's primary playmaker, from games BEFORE this one?
    mates = {}
    for m in roster.get((tm, gt), ()):
        pv = [x for x in hist.get(m, []) if x["tip"] < gt][-6:]
        if pv: mates[m] = statistics.mean(x["ast"] for x in pv)
    rank = sorted(mates, key=lambda m: -mates[m]).index(pl) + 1 if pl in mates else 99
    A.append(dict(pl=pl, gt=gt, line=line, odds=price, won=now["ast"] > line,
                  flagged=((tm, gt) in flag_games and (pl, gt) not in flag_players),
                  rank=rank))
print(f"{len(A)} assist overs on the board with a graded outcome")
fl = [r for r in A if r["flagged"]]
print(f"  of which {len(fl)} are on a TEAMMATE of a Model S pick")
print("")
def roi(rows): return sum((r["odds"]-1) if r["won"] else -1.0 for r in rows)/len(rows) if rows else 0.0
def show(rows, label, minn=25):
    n = len(rows)
    if n < minn:
        print(f"  {label:<48} n={n:<5} too few"); return
    w = sum(1 for r in rows if r["won"])
    avg = sum(r["odds"] for r in rows)/n
    print(f"  {label:<48} n={n:<5} {100*w/n:5.1f}%  ROI {100*roi(rows):+6.1f}%  be {100/avg:.1f}%")
print("="*104)
print("  CAN 'BACK A TEAMMATE'S ASSISTS' STAND ALONE AS A BET?")
print("="*104)
show(A, "EVERY assist over on the board (baseline)")
show(fl, "teammate of a Model S pick")
show([r for r in A if not r["flagged"]], "everyone else")
print("")
print("  and restricted to the team's PRIMARY playmaker, who would collect those assists:")
show([r for r in fl if r["rank"] == 1], "  flagged team, top assister")
show([r for r in fl if r["rank"] == 2], "  flagged team, second assister")
show([r for r in fl if r["rank"] >= 3], "  flagged team, third or lower")
show([r for r in A if not r["flagged"] and r["rank"] == 1], "  UNflagged team, top assister (control)")
print("")
print("="*104)
print("  PERMUTATION over the whole grid above")
print("="*104)
CELLS = [("teammate of a pick", lambda r: r["flagged"]),
         ("flagged, top assister", lambda r: r["flagged"] and r["rank"] == 1),
         ("flagged, second", lambda r: r["flagged"] and r["rank"] == 2),
         ("flagged, third+", lambda r: r["flagged"] and r["rank"] >= 3)]
def best(lab):
    b = -9e9; bl = ""
    for nm, sel in CELLS:
        g = [r for r in A if sel(r)]
        if len(g) < 25: continue
        v = sum((r["odds"]-1) if lab[id(r)] else -1.0 for r in g)/len(g)
        if v > b: b, bl = v, nm
    return b, bl
real, rlbl = best({id(r): r["won"] for r in A})
outs = [r["won"] for r in A]
T = 4000; beat = 0
for _ in range(T):
    random.shuffle(outs)
    v, _ = best({id(r): w for r, w in zip(A, outs)})
    if v >= real: beat += 1
print(f"  best cell: {rlbl}  ROI {100*real:+.1f}%   baseline {100*roi(A):+.1f}%")
print(f"  GLOBAL p = {beat/T:.4f}")
