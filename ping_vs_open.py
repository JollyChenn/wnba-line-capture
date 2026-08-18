# ping_vs_open.py - the +12.0% was graded at a price the card never told you to take.
# ---------------------------------------------------------------------------------------------
# grade_bets.py:128 grades OUR BET as cl[0] - the FIRST capture, usually the day before the game.
# model_card.py:184 pings `tonight[-1]` - the MOST RECENT quote, seconds before you read it.
# Those are different bets on the same player, at different numbers and different prices, and the
# Ogunbowale night proved the gap is real: 18.5 -> 19.5 -> 17.5, three pings, one player.
#
# So every ROI in this project computed from graded_bets - including yesterday's +12.0% headline -
# describes the OPENING line. The question that actually matters is whether the line you were
# PINGED AT wins, because that is the only one you can bet.
#
# This regrades the identical set of Model S bets three ways from the raw board archive:
#   OPEN   first quote for that game        (what graded_bets scores, and what I reported)
#   PING   last quote before tip            (what model_card puts in front of you)
#   BEST   the most favourable line offered (the ceiling, unreachable without hindsight)
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260922)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
SIGS = ("flip", "hotover", "overshoot"); BET_MKTS = ("pra", "pr", "pts")

# every OVER quote for a player-market-game, in time order, straight from the board archive
seq = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if not (t and o and ln is not None) or b.get("side") != "Over": continue
    pl, mk = (b.get("player") or "").lower(), b.get("market")
    tm = teamof.get(pl)
    if not tm: continue
    gt = game_for(tm, t)
    if gt: seq[(pl, mk, gt)].append((t, ln, o))
for v in seq.values(): v.sort()

tip_on = {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    tip_on[(hm, d2)] = t2; tip_on[(aw, d2)] = t2

R = []
drop = collections.Counter()
for r in load("graded_bets.csv"):
    if (r.get("result") or "").upper() not in ("WIN", "LOSS"): continue
    src, mk, pl = (r.get("src") or ""), (r.get("market") or ""), (r.get("player") or "").lower()
    if src not in SIGS or mk not in BET_MKTS: continue
    tm = teamof.get(pl)
    gt = tip_on.get((tm, r.get("date") or "")) if tm else None
    if not gt: drop["no game"] += 1; continue
    q = seq.get((pl, mk, gt), [])
    if len(q) < 2: drop["<2 quotes"] += 1; continue
    now = pgrow.get((pl, gt))
    if not now: drop["no box"] += 1; continue
    o_ln = f(r.get("line"))
    pv = prevline.get((pl, mk, gt))
    if pv is None or (o_ln is not None and o_ln - pv >= 0.5): continue     # gate 3: the star
    act = now[mk]
    o_t, o_l, o_o = q[0]                       # OPEN  - what graded_bets scores
    p_t, p_l, p_o = q[-1]                      # PING  - what the card shows you
    b_t, b_l, b_o = min(q, key=lambda x: (x[1], -x[2]))   # BEST - lowest line, best price at it
    if act == o_l or act == p_l: drop["push"] += 1; continue
    R.append(dict(pl=pl, mk=mk, gt=gt, date=r.get("date"), src=src, act=act,
                  o_l=o_l, o_o=o_o, o_w=act > o_l,
                  p_l=p_l, p_o=p_o, p_w=act > p_l,
                  b_l=b_l, b_o=b_o, b_w=act > b_l,
                  moved=round(p_l - o_l, 1), nq=len(q),
                  lead=(gt - o_t).total_seconds()/3600, late=(gt - p_t).total_seconds()/3600))
# one position per player-game, exactly as the card does it
best = {}
for r in sorted(R, key=lambda x: -x["p_o"]): best.setdefault((r["pl"], r["gt"]), r)
R = sorted(best.values(), key=lambda r: r["date"])
print(f"{len(R)} MODEL S bets regradable from the board archive   (dropped: {dict(drop)})")
print(f"  first quote lands a median {statistics.median([r['lead'] for r in R]):.1f}h before tip;"
      f" last quote {statistics.median([r['late'] for r in R]):.1f}h before tip")
print(f"  median quotes per bet: {statistics.median([r['nq'] for r in R]):.0f}")
print("")

def sc(rows, wk, ok):
    n = len(rows)
    w = sum(1 for r in rows if r[wk]); u = sum((r[ok]-1) if r[wk] else -1.0 for r in rows)
    return n, 100*w/n, u, 100*u/n
def pboot(rows, wk, ok, T=4000):
    bp = collections.defaultdict(list)
    for r in rows: bp[r["pl"]].append(r)
    keys = list(bp); o = []
    for _ in range(T):
        pick = [random.choice(keys) for _ in keys]
        g = [x for k in pick for x in bp[k]]
        o.append(100*sum((x[ok]-1) if x[wk] else -1.0 for x in g)/len(g))
    o.sort(); return o[int(T*.025)], o[int(T*.975)]
def show(rows, label, wk, ok):
    if len(rows) < 20: print(f"  {label:<44} n={len(rows)} too few"); return
    n, h, u, r_ = sc(rows, wk, ok); lo, hi = pboot(rows, wk, ok)
    print(f"  {label:<44} n={n:<4} {h:5.1f}%  {u:+7.2f}u  ROI {r_:+6.1f}%  95CI [{lo:+6.1f},{hi:+6.1f}]")

print("="*104)
print("  THE SAME BETS, THREE PRICES")
print("="*104)
show(R, "  OPEN  - first quote (what I reported)", "o_w", "o_o")
show(R, "  PING  - last quote (what you are shown)", "p_w", "p_o")
show(R, "  BEST  - lowest line offered (hindsight)", "b_w", "b_o")
print("")
print("="*104)
print("  WHY THEY DIFFER - the line moves between the two")
print("="*104)
mv = collections.Counter(r["moved"] for r in R)
print("  line move open -> ping: " + ", ".join(f"{k:+.1f}:{v}" for k, v in sorted(mv.items())))
same = [r for r in R if abs(r["moved"]) < 0.01]
print(f"  unchanged on {len(same)} of {len(R)} bets ({100*len(same)/len(R):.0f}%)")
print("")
show(same, "    unchanged line: OPEN", "o_w", "o_o")
show(same, "    unchanged line: PING", "p_w", "p_o")
diff = [r for r in R if abs(r["moved"]) >= 0.01]
show(diff, "    line MOVED: OPEN", "o_w", "o_o")
show(diff, "    line MOVED: PING", "p_w", "p_o")
print("")
print("  on the bets where the line never moved the two must agree except on price;")
print("  the gap between OPEN and PING lives entirely in the ones that moved.")
print("")
print("="*104)
print("  WAS IT EVEN A REAL PING? cloud_xbet:709 -> paper = src != 'model'")
print("="*104)
print("  only src='model' (cold/shrink unders) ever reached the real-money BET ping. flip,")
print("  hotover and overshoot were routed to `forward` - logged for CLV, never pinged as a bet.")
print("  Model S is built entirely from those three, so every bet below was PAPER at capture time")
print("  and only became a live recommendation when model_card started posting it.")
print("")
mf = [r for r in load("model_forward.csv") if (r.get("result") or "").upper() in ("WIN", "LOSS")]
print(f"  bets model_card has actually put in front of you and that settled: {len(mf)}")
