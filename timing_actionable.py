# timing_redo.py - re-test WHEN to bet, using the game-anchored board logic.
# ---------------------------------------------------------------------------------------------
# My "bet on the alert, waiting costs 4.7pp" finding came from the OLD block logic, which
# bucketed quotes by "started within 30h of tip" - the bug that put half of all live lines into
# the previous-game bucket. So the timing conclusion was built on the same broken foundation and
# has to be redone.
#
# Arike Ogunbowale on 2026-08-18 is the case that prompted it: her line went 19.5 -> 18.5 -> 19.5
# -> 18.5 -> 17.5, and the last one was both the LOWEST number and the best price (2.00). For an
# over, lower is unambiguously better - so waiting won, twice.
#
# Three strategies, same bets, graded honestly:
#   FIRST   take the first quote we ever see for that game
#   LAST    take the last quote before tip
#   BEST    the lowest line, tie-broken on price - unattainable in practice, it is the ceiling
import csv, os, sys, math, statistics, datetime, collections
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

MKTS = ("pra", "pr", "pts"); SIGS = ("flip", "hotover", "overshoot")
gm = {g.get("game_id"): (g.get("date", ""), ts(g.get("tip"))) for g in load("data/games_2026.csv")}
plog = collections.defaultdict(list); team = {}
for r in load("data/box_2026.csv"):
    dt, tp = gm.get(r.get("game_id"), ("", None))
    if not dt or tp is None: continue
    p_, rb, a = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    pl = (r.get("player") or "").lower()
    plog[pl].append(dict(tip=tp, date=dt, pts=p_, pra=p_+rb+a, pr=p_+rb))
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
    if len(seq) < 2 or not rec: continue
    earlier = sorted(g for (p2, m2, g) in bygame if p2 == pl and m2 == mk and g < gt)
    pv = bygame[(pl, mk, earlier[-1])][-1][1] if earlier else None
    if pv is None or seq[-1][1] - pv >= 0.5: continue          # MODEL S starred
    seen.add((pl, mk, gt))
    first = seq[0]; last = seq[-1]
    best = min(seq, key=lambda x: (x[1], -x[2]))               # lowest line, then best price
    K.append(dict(pl=pl, mk=mk, date=rec["date"], actual=rec[mk],
                  f_ln=first[1], f_od=first[2], l_ln=last[1], l_od=last[2],
                  b_ln=best[1], b_od=best[2], nq=len(seq)))
byday = collections.defaultdict(list)
for r in K: byday[r["date"]].append(r)
for dd in list(byday):
    bp = {}
    for r in sorted(byday[dd], key=lambda x: -x["l_od"]): bp.setdefault(r["pl"], r)
    byday[dd] = list(bp.values())
K = [r for v in byday.values() for r in v]
print(f"{len(K)} starred Model S bets with 2+ quotes for the game (one position per player)")
print("")


def score(rows, lk, ok):
    n = len(rows)
    if not n: return 0,0,0.0
    w = sum(1 for r in rows if r["actual"] > r[lk])
    u = sum((r[ok]-1) if r["actual"] > r[lk] else -1.0 for r in rows if r["actual"] != r[lk])
    return n, w, u
print("="*100)
print("  IS THERE AN ACTIONABLE RULE? you can see, at bet time, whether the line has RISEN")
print("  above where it opened. That is knowable without hindsight.")
print("="*100)
risen = [r for r in K if r["l_ln"] > r["f_ln"]]
notrisen = [r for r in K if r["l_ln"] <= r["f_ln"]]
for lbl, rows, lk, ok in (("bet LAST, all", K, "l_ln", "l_od"),
                          ("bet LAST, only if line has NOT risen", notrisen, "l_ln", "l_od"),
                          ("bet LAST, only where it HAS risen", risen, "l_ln", "l_od"),
                          ("bet FIRST, all  <- current advice", K, "f_ln", "f_od")):
    n, w, u = score(rows, lk, ok)
    if n < 10:
        print(f"  {lbl:<42} n={n} too few"); continue
    print(f"  {lbl:<42} n={n:<4} {100*w/n:5.1f}%  {u:+7.2f}u  ROI {100*u/n:+6.1f}%")
print("")
print("  and the same, restricted to bets where a better line DID appear:")
imp = [r for r in K if r["b_ln"] < r["f_ln"]]
for lbl, rows, lk, ok in (("  those bets, taken FIRST", imp, "f_ln", "f_od"),
                          ("  those bets, taken LAST", imp, "l_ln", "l_od"),
                          ("  those bets, taken at the BEST", imp, "b_ln", "b_od")):
    n, w, u = score(rows, lk, ok)
    if n < 10: continue
    print(f"  {lbl:<42} n={n:<4} {100*w/n:5.1f}%  {u:+7.2f}u  ROI {100*u/n:+6.1f}%")
print("")
print("  NOTE the trap: 'a better line appeared' is only knowable AFTER it appears. By the time")
print("  you can see it you have either already bet, or you have been waiting - and waiting is")
print("  what the LAST column measures.")
