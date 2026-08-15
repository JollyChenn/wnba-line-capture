# samegame_test.py - the parlay edge appears to live ENTIRELY in same-game pairs. Check it.
# ---------------------------------------------------------------------------------------------
# The audit split 38 pairs into 22 same-game (+85.3% ROI, 54.5% hit) and 16 different-game
# (-36.5% ROI, 18.8% hit). If that holds it inverts the practical advice, because tonight's pair
# - Hamby in LA@WSH and Smith in MIN@LV - is a DIFFERENT-game pair, i.e. the losing bucket.
#
# It is also the mechanism you would predict: two players in one game share pace and possessions,
# so their overs cluster. Different games share nothing. But n=22 and n=16 are small, and every
# exciting split I have looked at today has died under a null test, so it gets the same treatment.
import csv, os, sys, math, random, itertools, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260821)
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
    if not dt: continue
    p_, rb, a = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    pl = (r.get("player") or "").lower()
    plog[pl].append(dict(tip=tp, pra=p_+rb+a, pr=p_+rb, pts=p_))
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
    BETS.append(dict(pl=pl, name=(b.get("player") or "").split()[-1], tm=tm, tip=gt,
                     day=gt.strftime("%Y%m%d"), odds=seq[-1][2], won=rec[mk] > line))
byday = collections.defaultdict(list)
for r in BETS: byday[r["day"]].append(r)
for d in list(byday):
    best = {}
    for r in sorted(byday[d], key=lambda x: -x["odds"]): best.setdefault(r["pl"], r)
    byday[d] = sorted(best.values(), key=lambda r: r["tip"])
days = sorted(byday)
flat = [r for d in days for r in byday[d]]
P = sum(1 for r in flat if r["won"])/len(flat)
print(f"{len(flat)} Model S bets, base hit rate {100*P:.1f}%")
print("")
print("="*100)
print("  ALL POSSIBLE PAIRS (not just the ones tip-time pairing happens to make)")
print("  - using every pair overcounts for P&L, but for a HIT-RATE comparison it is the")
print("    right denominator: we want P(both win | same game) vs P(both win | different)")
print("="*100)
sg = dg = 0; sgw = dgw = 0
for d in days:
    for a, b2 in itertools.combinations(byday[d], 2):
        both = a["won"] and b2["won"]
        if a["tip"] == b2["tip"]: sg += 1; sgw += both
        else: dg += 1; dgw += both
print(f"  SAME GAME       {sg:>4} pairs   both won {sgw:>3}  = {100*sgw/sg if sg else 0:5.1f}%")
print(f"  DIFFERENT GAME  {dg:>4} pairs   both won {dgw:>3}  = {100*dgw/dg if dg else 0:5.1f}%")
print(f"  independence would predict {100*P*P:.1f}% for both")
print("")
print("  PERMUTATION TEST: shuffle which bets belong to which game, keeping the day and the")
print("  outcomes fixed. If same-game clustering is real, the real gap should be extreme.")
real_gap = (sgw/sg if sg else 0) - (dgw/dg if dg else 0)
T = 10000; extreme = 0
for _ in range(T):
    s2 = d2 = 0; s2w = d2w = 0
    for d in days:
        v = byday[d][:]
        gamelist = [r["tip"] for r in v]
        random.shuffle(gamelist)
        vv = [dict(r, tip=g) for r, g in zip(v, gamelist)]
        for a, b2 in itertools.combinations(vv, 2):
            both = a["won"] and b2["won"]
            if a["tip"] == b2["tip"]: s2 += 1; s2w += both
            else: d2 += 1; d2w += both
    gap = (s2w/s2 if s2 else 0) - (d2w/d2 if d2 else 0)
    if gap >= real_gap: extreme += 1
print(f"  real gap {100*real_gap:+.1f}pp   shuffled gap >= real in {extreme}/{T} = p {extreme/T:.4f}")
print("")
print("="*100)
print("  WHAT IT MEANS FOR A PAIR YOU CAN ACTUALLY BET")
print("="*100)
avg = sum(r["odds"] for r in flat)/len(flat)
for lbl, hit, n in (("same game", sgw/sg if sg else 0, sg), ("different game", dgw/dg if dg else 0, dg)):
    roi = hit*avg*avg - 1
    print(f"  {lbl:<16} pair hit {100*hit:5.1f}%  x payout {avg*avg:.2f}  ->  ROI {100*roi:+6.1f}%"
          f"   (break-even {100/(avg*avg):.1f}%)")
print("")
print("  NOTE: books commonly refuse or re-price SAME-GAME accumulators precisely because of")
print("  this correlation. The 3.235 quote that was verified was a DIFFERENT-game pair.")
