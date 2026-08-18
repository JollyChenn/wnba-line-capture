# timing_headtohead.py - first vs last vs every-line, counted rather than averaged.
# ---------------------------------------------------------------------------------------------
# Averages hide the thing you actually want to know: on the bets where the two strategies
# DIFFER, which one wins more often, and by how many units. On the 52% of bets where the line
# never moved, first and last are the same ticket and tell you nothing - they just dilute the
# comparison. So this counts only the disagreements, and adds the third option: take a bet at
# EVERY distinct line the book offers.
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
    if len(seq) < 1 or not rec: continue
    earlier = sorted(g for (p2, m2, g) in bygame if p2 == pl and m2 == mk and g < gt)
    pv = bygame[(pl, mk, earlier[-1])][-1][1] if earlier else None
    if pv is None or seq[-1][1] - pv >= 0.5: continue
    seen.add((pl, mk, gt))
    # DISTINCT lines in the order the book OFFERED them - time order, not value order.
    # Sorting by value silently turns "take each improvement" into "take the lowest line",
    # which is hindsight, and it is why that row came out with exactly one ticket per bet.
    perline, order = {}, []
    for t, ln, o in seq:
        if ln not in perline:
            perline[ln] = o; order.append(ln)
        elif o > perline[ln]:
            perline[ln] = o
    K.append(dict(pl=pl, name=b.get("player"), mk=mk, date=rec["date"], actual=rec[mk],
                  first=(seq[0][1], seq[0][2]), last=(seq[-1][1], seq[-1][2]),
                  lines=[(ln, perline[ln]) for ln in order]))
byday = collections.defaultdict(list)
for r in K: byday[r["date"]].append(r)
for dd in list(byday):
    bp = {}
    for r in sorted(byday[dd], key=lambda x: -x["last"][1]): bp.setdefault(r["pl"], r)
    byday[dd] = list(bp.values())
K = [r for v in byday.values() for r in v]

def pnl(ln, od, actual):
    if actual == ln: return 0.0
    return (od - 1) if actual > ln else -1.0

same = [r for r in K if r["first"][0] == r["last"][0]]
diff = [r for r in K if r["first"][0] != r["last"][0]]
print(f"{len(K)} starred bets.  line never moved on {len(same)} of them ({100*len(same)/len(K):.0f}%)")
print(f"the two strategies can only differ on the other {len(diff)}.")
print("")
print("="*100)
print("  ONLY THE BETS WHERE FIRST AND LAST DISAGREE")
print("="*100)
fw = lw = tie = 0; fu = lu = 0.0
for r in diff:
    a = pnl(r["first"][0], r["first"][1], r["actual"])
    b = pnl(r["last"][0], r["last"][1], r["actual"])
    fu += a; lu += b
    if a > b: fw += 1
    elif b > a: lw += 1
    else: tie += 1
print(f"  FIRST was the better ticket on   {fw} of {len(diff)}")
print(f"  LAST was the better ticket on    {lw} of {len(diff)}")
print(f"  identical outcome                {tie}")
print("")
print(f"  units on those {len(diff)} bets:   FIRST {fu:+.2f}u    LAST {lu:+.2f}u    "
      f"difference {fu-lu:+.2f}u")
print("")
print("  every disagreement, one line each:")
print(f"  {'player':<20}{'first':>14}{'last':>14}{'got':>7}   winner")
for r in sorted(diff, key=lambda x: x["date"]):
    a = pnl(r["first"][0], r["first"][1], r["actual"])
    b = pnl(r["last"][0], r["last"][1], r["actual"])
    win = "FIRST" if a > b else ("LAST" if b > a else "same")
    print(f"  {r['name'][:19]:<20}{r['first'][0]:>8.1f}@{r['first'][1]:<5.2f}"
          f"{r['last'][0]:>8.1f}@{r['last'][1]:<5.2f}{r['actual']:>7.0f}   {win}")
print("")
print("="*100)
print("  AND THE THIRD OPTION: a ticket at EVERY distinct line the book offered")
print("="*100)
tot_tickets = sum(len(r["lines"]) for r in K)
eu = sum(pnl(ln, od, r["actual"]) for r in K for ln, od in r["lines"])
fu_all = sum(pnl(r["first"][0], r["first"][1], r["actual"]) for r in K)
lu_all = sum(pnl(r["last"][0], r["last"][1], r["actual"]) for r in K)
print(f"  FIRST only      {len(K):>4} tickets  {len(K):>5.0f}u risked  {fu_all:+8.2f}u")
print(f"  LAST only       {len(K):>4} tickets  {len(K):>5.0f}u risked  {lu_all:+8.2f}u")
print(f"  EVERY line      {tot_tickets:>4} tickets  {tot_tickets:>5.0f}u risked  {eu:+8.2f}u")
print("")
print(f"  per unit risked:  FIRST {100*fu_all/len(K):+.1f}%   LAST {100*lu_all/len(K):+.1f}%   "
      f"EVERY {100*eu/tot_tickets:+.1f}%")
print("")
multi = [r for r in K if len(r["lines"]) > 1]
print(f"  {len(multi)} of {len(K)} bets had more than one line on offer, so 'every line' means")
print(f"  {tot_tickets - len(K)} extra tickets - all on players you were already betting.")
