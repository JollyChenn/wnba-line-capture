# usage_dim.py - teammate and usage features, tested on the WHOLE BOARD rather than on 99 bets.
# ---------------------------------------------------------------------------------------------
# power_check.py showed the real problem: slicing 99 Model S bets cannot resolve anything below a
# ~40% ROI cell, and a coin flip on those same bets produced +24.7%. So the fix is not a cleverer
# filter, it is a bigger denominator.
#
# These features are computable for EVERY player-market-game on the board - about 6000 rows, not
# 99 - because they come from the box score and the board, not from our signal engine. If a
# teammate/usage effect is real it will show up there with power behind it, and it would then be
# a NEW SIGNAL rather than a filter on an existing one.
#
# Features, all strictly from games BEFORE the one being predicted:
#   USAGE SHARE   her (FGA + 0.44*FTA + TOV) as a fraction of her team's, trailing 5
#   USAGE TREND   trailing 3 minus trailing 10 - is the offence flowing to her more lately
#   MINUTES TREND same for minutes
#   TEAMMATE OUT  a top-3-usage teammate from her recent games does not appear in this one
#   FORM vs LINE  her trailing 5 production minus tonight's number
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260903)
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

MKTS = ("pts", "pra", "pr", "pa", "reb", "ast", "ra")
gmeta = {}
for g in load("data/games_2026.csv"):
    t = ts(g.get("tip"))
    if t: gmeta[g.get("game_id")] = (g.get("date", ""), t, g.get("home"), g.get("away"))

# ---- per player-game box line, plus team totals for usage share --------------------------------
pg = {}
teamgame = collections.defaultdict(lambda: collections.defaultdict(float))
for r in load("data/box_2026.csv"):
    gid = r.get("game_id")
    if gid not in gmeta: continue
    dt, tp, hm, aw = gmeta[gid]
    tm = r.get("team"); pl = (r.get("player") or "").lower()
    p_, rb, a = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    fga, fta, to, mn = f(r.get("fga")) or 0, f(r.get("fta")) or 0, f(r.get("to")) or 0, f(r.get("min")) or 0
    use = fga + 0.44*fta + to
    pg[(pl, tp)] = dict(pl=pl, tm=tm, tip=tp, date=dt, min=mn, use=use,
                        pts=p_, reb=rb, ast=a, pra=p_+rb+a, pr=p_+rb, pa=p_+a, ra=rb+a)
    teamgame[(tm, tp)]["use"] += use
    teamgame[(tm, tp)]["min"] += mn

hist = collections.defaultdict(list)
for (pl, tp), row in pg.items(): hist[pl].append(row)
for v in hist.values(): v.sort(key=lambda x: x["tip"])
roster = collections.defaultdict(set)                 # who appeared for a team in a given game
for (pl, tp), row in pg.items(): roster[(row["tm"], tp)].add(pl)

def prior(pl, tp, n):
    return [x for x in hist.get(pl, []) if x["tip"] < tp][-n:]

# ---- the board: one Over quote per player-market-game -------------------------------------------
tips_of = collections.defaultdict(list)
for gid, (dt, tp, hm, aw) in gmeta.items():
    tips_of[hm].append(tp); tips_of[aw].append(tp)
for v in tips_of.values(): v.sort()
teamof = {row["pl"]: row["tm"] for row in pg.values()}
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
    tm = teamof.get(pl)
    if not tm: continue
    for t, o in sorted(v):
        g2 = game_for(tm, t)
        if g2: bygame[(pl, mk, g2)].append((t, ln, o))
for v in bygame.values(): v.sort()

K = []
for (pl, mk, tp), seq in bygame.items():
    now = pg.get((pl, tp))
    if not now: continue
    line, price = seq[-1][1], seq[-1][2]
    if now[mk] == line: continue
    p5, p10, p3 = prior(pl, tp, 5), prior(pl, tp, 10), prior(pl, tp, 3)
    if len(p5) < 4: continue
    def share(rows):
        tot = [teamgame.get((r["tm"], r["tip"]), {}).get("use", 0) for r in rows]
        return statistics.mean([r["use"]/t for r, t in zip(rows, tot) if t > 0]) if any(t > 0 for t in tot) else None
    us5 = share(p5); us3 = share(p3) if len(p3) >= 3 else None; us10 = share(p10) if len(p10) >= 6 else None
    mn3 = statistics.mean(r["min"] for r in p3) if len(p3) >= 3 else None
    mn10 = statistics.mean(r["min"] for r in p10) if len(p10) >= 6 else None
    # teammate out: top-3 usage teammates over her recent games who are absent tonight
    mates = collections.Counter()
    for r in p5:
        for m in roster.get((r["tm"], r["tip"]), ()):
            if m != pl: mates[m] += pg[(m, r["tip"])]["use"]
    top3 = [m for m, _ in mates.most_common(3)]
    here = roster.get((now["tm"], tp), set())
    out3 = sum(1 for m in top3 if m not in here)
    K.append(dict(pl=pl, mk=mk, date=now["date"], tip=tp, line=line, odds=price,
                  won=now[mk] > line,
                  use5=us5, use_trend=(None if (us3 is None or us10 is None) else us3-us10),
                  min_trend=(None if (mn3 is None or mn10 is None) else mn3-mn10),
                  mates_out=out3,
                  form_gap=statistics.mean(r[mk] for r in p5) - line))
print(f"{len(K)} player-market-games on the board with full box history")
for lbl, key in (("usage share", "use5"), ("usage trend", "use_trend"),
                 ("minutes trend", "min_trend"), ("form gap", "form_gap")):
    print(f"    {lbl:<16} {sum(1 for r in K if r.get(key) is not None):>5} of {len(K)}")
print(f"    teammates out    {collections.Counter(r['mates_out'] for r in K)}")
print("")

def roi(rows): return sum((r["odds"]-1) if r["won"] else -1.0 for r in rows)/len(rows) if rows else 0.0
def show(rows, label, minn=80):
    n = len(rows)
    if n < minn:
        print(f"  {label:<44} n={n:<5} too few"); return
    w = sum(1 for r in rows if r["won"])
    avg = sum(r["odds"] for r in rows)/n
    print(f"  {label:<44} n={n:<5} {100*w/n:5.1f}%  ROI {100*roi(rows):+6.1f}%  be {100/avg:.1f}%")

CELLS = []
def reg(name, sel):
    g = [r for r in K if sel(r)]
    if len(g) >= 80: CELLS.append((name, sel))
    show(g, f"  {name}")

print("="*104)
print(f"  BASELINE - every over on the board: ROI {100*roi(K):+.1f}%   (n={len(K)})")
print("="*104)
print("")
print("  1. TEAMMATES OUT - top-3 usage teammates missing tonight")
for k in (0, 1, 2):
    reg(f"{k} of her top-3 usage teammates out", lambda r, k=k: r["mates_out"] == k)
reg("1+ top-3 teammate out", lambda r: r["mates_out"] >= 1)
print("")
print("  2. USAGE TREND - last 3 games minus last 10")
ut = sorted(r["use_trend"] for r in K if r["use_trend"] is not None)
if ut:
    m = ut[len(ut)//2]
    reg("usage RISING (above median trend)", lambda r, m=m: r["use_trend"] is not None and r["use_trend"] >= m)
    reg("usage falling", lambda r, m=m: r["use_trend"] is not None and r["use_trend"] < m)
    hi = ut[int(len(ut)*0.8)]
    reg("usage rising HARD (top 20%)", lambda r, h=hi: r["use_trend"] is not None and r["use_trend"] >= h)
print("")
print("  3. MINUTES TREND")
mt = sorted(r["min_trend"] for r in K if r["min_trend"] is not None)
if mt:
    m = mt[len(mt)//2]
    reg("minutes RISING", lambda r, m=m: r["min_trend"] is not None and r["min_trend"] >= m)
    reg("minutes falling", lambda r, m=m: r["min_trend"] is not None and r["min_trend"] < m)
print("")
print("  4. FORM vs LINE - trailing 5 production minus tonight's number")
fgs = sorted(r["form_gap"] for r in K)
for q, lbl in ((0.8, "form 20% above the line"), (0.5, "form above median gap"),
               (0.2, "form 20% below the line")):
    thr = fgs[int(len(fgs)*q)]
    if q >= 0.5: reg(lbl, lambda r, t=thr: r["form_gap"] >= t)
    else: reg(lbl, lambda r, t=thr: r["form_gap"] <= t)
print("")
print("="*104)
print(f"  GLOBAL PERMUTATION over all {len(CELLS)} cells, {len(K)} bets - THIS time with power")
print("="*104)
def best_of(lab):
    b = -9e9; bl = ""
    for nm, sel in CELLS:
        g = [r for r in K if sel(r)]
        if len(g) < 80: continue
        v = sum((r["odds"]-1) if lab[id(r)] else -1.0 for r in g)/len(g)
        if v > b: b, bl = v, nm
    return b, bl
real, rlbl = best_of({id(r): r["won"] for r in K})
outs = [r["won"] for r in K]
T = 1000; beat = 0; sims = []
for _ in range(T):
    sh = outs[:]; random.shuffle(sh)
    v, _ = best_of({id(r): w for r, w in zip(K, sh)})
    sims.append(v)
    if v >= real: beat += 1
sims.sort()
print(f"  BEST CELL: {rlbl}  ROI {100*real:+.1f}%")
print(f"  shuffled best-of-grid: median {100*sims[T//2]:+.1f}%  p95 {100*sims[int(T*0.95)]:+.1f}%")
print(f"  GLOBAL p = {beat/T:.4f}")
print("")
print(f"  note the noise ceiling here: p95 is {100*sims[int(T*0.95)]:+.1f}% on cells of hundreds,")
print(f"  against +42.5% on the 99-bet sweep. THIS is what power buys.")
