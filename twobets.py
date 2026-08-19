# twobets.py - two markets on one player. Second opinion, or the same opinion twice?
# ---------------------------------------------------------------------------------------------
# gate4.py came back empty: graded_bets has ZERO player-games with two qualifying markets, because
# cloud_xbet.py:678 already collapses each player to her single highest-confidence pick before
# anything is logged. So the double has never been recorded as a bet and cannot be measured there.
#
# But it can be measured on the BOARD, which carries every line the book offered whether we bet it
# or not. For every player-game where 1xbet posted BOTH a PTS line and a PR line (or any pair of
# the three Model S markets), grade both overs off the box score and ask how often they land
# together. Thousands of player-games instead of zero, and it answers the real question:
#
#   if P(both) is close to P(A) x P(B), the two bets are near-independent and a second unit buys
#   genuine diversification.
#   if P(both) is much HIGHER, they are one bet in two costumes - taking both is 2u of leverage on
#   a single player's evening, not two positions.
#
# The arithmetic is not in doubt for the nested pair: PR = PTS + REB, so PR over 13.5 cannot land
# unless she also clears roughly the PTS number. The point of measuring is to size the effect.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260819)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
MK = ("pts", "pr", "pra")

# last Over quote per player-market-game, straight from the board
last = {}
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if not (t and o and ln is not None) or b.get("side") != "Over": continue
    pl, mk = (b.get("player") or "").lower(), b.get("market")
    if mk not in MK: continue
    tm = teamof.get(pl)
    if not tm: continue
    gt = game_for(tm, t)
    if not gt: continue
    k = (pl, mk, gt)
    if k not in last or t > last[k][0]: last[k] = (t, ln, o)

pg = collections.defaultdict(dict)
for (pl, mk, gt), (t, ln, o) in last.items():
    now = pgrow.get((pl, gt))
    if not now or now[mk] == ln: continue
    pg[(pl, gt)][mk] = dict(ln=ln, od=o, won=now[mk] > ln, act=now[mk])

print(f"{len(pg)} player-games with at least one board line in pts/pr/pra")
cnt = collections.Counter(len(v) for v in pg.values())
print("  markets offered per player-game: " + ", ".join(f"{k}:{v}" for k, v in sorted(cnt.items())))
print("")

PAIRS = [("pts", "pr"), ("pts", "pra"), ("pr", "pra")]
print("="*104)
print("  HOW OFTEN DO TWO OVERS ON THE SAME PLAYER LAND TOGETHER?")
print("="*104)
print(f"  {'pair':<14}{'n':>6}{'P(A)':>8}{'P(B)':>8}{'P(both)':>10}{'if indep':>10}{'lift':>9}{'agree':>9}")
for a, b in PAIRS:
    g = [v for v in pg.values() if a in v and b in v]
    if len(g) < 30: print(f"  {a}+{b:<9}{len(g)} too few"); continue
    pa = sum(1 for v in g if v[a]["won"])/len(g)
    pb = sum(1 for v in g if v[b]["won"])/len(g)
    both = sum(1 for v in g if v[a]["won"] and v[b]["won"])/len(g)
    agree = sum(1 for v in g if v[a]["won"] == v[b]["won"])/len(g)
    print(f"  {a}+{b:<9}{len(g):>6}{100*pa:>7.1f}%{100*pb:>7.1f}%{100*both:>9.1f}%"
          f"{100*pa*pb:>9.1f}%{100*(both-pa*pb):>+8.1f}{100*agree:>8.1f}%")
print("")
print("  'agree' = both won or both lost. 50% means unrelated. The closer to 100%, the more the")
print("  second bet is just the first bet again.")
print("")
print("="*104)
print("  WHAT DOUBLING DOES TO A NIGHT - same edge, two units, one player")
print("="*104)
g = [v for v in pg.values() if "pts" in v and "pr" in v]
if len(g) >= 30:
    outs = collections.Counter()
    for v in g:
        outs[(v["pts"]["won"], v["pr"]["won"])] += 1
    n = len(g)
    print(f"  on {n} player-games where both lines existed:")
    print(f"    both overs land      {outs[(True,True)]:>5}  ({100*outs[(True,True)]/n:4.1f}%)  -> +2 winners")
    print(f"    both miss            {outs[(False,False)]:>5}  ({100*outs[(False,False)]/n:4.1f}%)  -> -2u, same night")
    print(f"    split                {outs[(True,False)]+outs[(False,True)]:>5}"
          f"  ({100*(outs[(True,False)]+outs[(False,True)])/n:4.1f}%)")
    p2 = outs[(False,False)]/n
    solo = sum(1 for v in g if not v["pts"]["won"])/n
    print("")
    print(f"  chance of losing BOTH units on one player: {100*p2:.1f}%")
    print(f"  chance of losing a single unit on her:     {100*solo:.1f}%")
    print(f"  if the two were independent, losing both would be {100*solo*(1-sum(1 for v in g if v['pr']['won'])/n)/max(solo,1e-9)*solo:.1f}%"
          if False else
          f"  independent double-loss would be {100*(1-sum(1 for v in g if v['pts']['won'])/n)*(1-sum(1 for v in g if v['pr']['won'])/n):.1f}%")
print("")
print("="*104)
print("  AND IS THE SECOND LINE EVEN THE BETTER BET? cushion vs price")
print("="*104)
def med_before(pl, mk, gt):
    v = [r[mk] for r in hist.get(pl, []) if r["tip"] < gt]
    return statistics.median(v[-10:]) if len(v) >= 3 else None
rows = []
for (pl, gt), v in pg.items():
    for mk, d in v.items():
        m = med_before(pl, mk, gt)
        if m is None: continue
        rows.append(dict(pl=pl, mk=mk, gt=gt, cush=m - d["ln"], od=d["od"], won=d["won"]))
deep = [r for r in rows if r["cush"] >= 3]
print(f"  board-wide overs with a 3+ cushion below her median: {len(deep)}")
if len(deep) >= 60:
    q = sorted(r["od"] for r in deep); lo, hi = q[len(q)//3], q[2*len(q)//3]
    for lbl, sel in (("shortest price third", lambda r: r["od"] <= lo),
                     ("middle third",         lambda r: lo < r["od"] <= hi),
                     ("longest price third",  lambda r: r["od"] > hi)):
        s = [r for r in deep if sel(r)]
        if len(s) < 20: continue
        w = sum(1 for r in s if r["won"]); u = sum((r["od"]-1) if r["won"] else -1.0 for r in s)
        print(f"    {lbl:<24} n={len(s):<5}{100*w/len(s):>6.1f}%   ROI {100*u/len(s):+6.1f}%")
    print("")
    print("  if the LONGEST price third is the worst, then 'keep the best price' is picking the")
    print("  position the book is most confident about, and cushion is the better tiebreak.")
