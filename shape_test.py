# shape_test.py - not the NET line move (that is the star) but the SHAPE of the path.
# ---------------------------------------------------------------------------------------------
# Does "raised, then cut, then raised" mean something different from a line that simply sat
# still? And does the ODDS direction, at a fixed line, carry information the line does not?
#
# CAREFUL ON ONE THING. Every odds comparison here is taken AT THE SAME LINE. Four separate
# findings today collapsed because two quoted numbers turned out to belong to different lines
# or different games, so an odds path is only computed within one line's own quote series.
import csv, os, sys, math, datetime, collections
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

MKTS = ("pra", "pr", "pts")
gm = {g.get("game_id"): (g.get("date",""), ts(g.get("tip"))) for g in load("data/games_2026.csv")}
plog = collections.defaultdict(list); team = {}
for r in load("data/box_2026.csv"):
    dt, tp = gm.get(r.get("game_id"), ("", None))
    if not dt: continue
    p_, rb, a = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    pl = (r.get("player") or "").lower()
    plog[pl].append(dict(date=dt, tip=tp, pts=p_, reb=rb, ast=a,
                         pra=p_+rb+a, pr=p_+rb, pts_=p_))
    team[pl] = r.get("team")
val = lambda rec, mk: rec["pra"] if mk == "pra" else (rec["pr"] if mk == "pr" else rec["pts"])

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
        gt = game_for(tm, t)
        if gt: bygame[(pl, mk, gt)].append((t, ln, o))
for v in bygame.values(): v.sort()

SIGS = ("flip", "hotover", "overshoot")
seen, R = set(), []
for b in sorted(load("bets_log.csv"), key=lambda r: r.get("captured_utc") or ""):
    if b.get("side") != "Over" or b.get("src") not in SIGS: continue
    pl, mk = (b.get("player") or "").lower(), b.get("market")
    if mk not in MKTS: continue
    t0 = ts(b.get("captured_utc")); tm = team.get(pl)
    if not (t0 and tm): continue
    gt = game_for(tm, t0)
    if not gt or (pl, mk, gt) in seen: continue
    seq = bygame.get((pl, mk, gt), [])
    if len(seq) < 1: continue
    rec = next((g for g in plog.get(pl, []) if g["tip"] == gt), None)
    if not rec: continue
    seen.add((pl, mk, gt))
    line_now = seq[-1][1]
    earlier = sorted(g for (p2, m2, g) in bygame if p2 == pl and m2 == mk and g < gt)
    pv = bygame[(pl, mk, earlier[-1])][-1][1] if earlier else None
    if pv is None or line_now - pv >= 0.5: continue        # MODEL S bets only
    lines = [x[1] for x in seq]
    chg = [b_-a_ for a_, b_ in zip(lines, lines[1:]) if b_ != a_]
    ups = sum(1 for c in chg if c > 0); dns = sum(1 for c in chg if c < 0)
    same = [x for x in seq if x[1] == line_now]
    odds_mv = (same[-1][2]/same[0][2] - 1) if len(same) >= 2 else 0.0
    R.append(dict(pl=pl, mk=mk, gt=gt, line=line_now, odds=seq[-1][2],
                  nchg=len(chg), ups=ups, dns=dns, odds_mv=odds_mv,
                  won=val(rec, mk) > line_now))

def st(rows, label, minn=10):
    n = len(rows)
    if n < minn:
        print(f"  {label:<44} n={n:<4} too few"); return
    w = sum(1 for r in rows if r["won"])
    u = sum((r["odds"]-1) if r["won"] else -1.0 for r in rows)
    print(f"  {label:<44} n={n:<4} {100*w/n:5.1f}%  {u:+7.2f}u  ROI {100*u/n:+6.1f}%")

print(f"{len(R)} Model S bets with a full intraday quote path")
print("")
print("="*92)
print("  1. HOW MANY TIMES DID THE LINE MOVE BEFORE TIP?")
print("="*92)
st([r for r in R if r["nchg"] == 0], "  never moved (one number all day)")
st([r for r in R if r["nchg"] == 1], "  moved once")
st([r for r in R if r["nchg"] >= 2], "  moved 2+ times (the zigzag)")
print("")
print("="*92)
print("  2. THE SHAPE OF THE PATH")
print("="*92)
st([r for r in R if r["nchg"] == 0],                          "  flat")
st([r for r in R if r["ups"] > 0 and r["dns"] == 0],          "  only ever went UP")
st([r for r in R if r["dns"] > 0 and r["ups"] == 0],          "  only ever went DOWN")
st([r for r in R if r["ups"] > 0 and r["dns"] > 0],           "  ZIGZAG (both directions)")
print("")
print("="*92)
print("  3. ODDS PATH AT THE FINAL LINE - does the price say what the line does not?")
print("="*92)
st([r for r in R if r["odds_mv"] <= -0.02], "  odds SHORTENED 2%+ (money on the over)")
st([r for r in R if -0.02 < r["odds_mv"] < -0.0001], "  odds shortened slightly")
st([r for r in R if abs(r["odds_mv"]) <= 0.0001], "  odds unchanged")
st([r for r in R if 0.0001 < r["odds_mv"] < 0.02], "  odds lengthened slightly")
st([r for r in R if r["odds_mv"] >= 0.02], "  odds LENGTHENED 2%+ (money on the under)")
print("")
st([r for r in R if r["odds_mv"] < 0],  "  ALL shortened")
st([r for r in R if r["odds_mv"] > 0],  "  ALL lengthened")
st([r for r in R if r["odds_mv"] == 0], "  ALL unchanged")
