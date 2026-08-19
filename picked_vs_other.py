# picked_vs_other.py - does the market gate 4 DISCARDS carry the same edge as the one it keeps?
# ---------------------------------------------------------------------------------------------
# When the card said "Thornton PTS 8.5, and PR 13.5 also qualified", I told you taking both was a
# staking decision because each leg presumably carries the same edge. That was an assumption, and
# sidebets.py suggests it is wrong: every board market belonging to a Model S player that night
# returns +1.2% on the over, against +18.7% for Model S itself. Those two cannot both be true
# unless the markets we DON'T pick are much worse than the one we do.
#
# So split them cleanly: the exact market Model S bet, versus every other market the book offered
# on that same player in that same game. Same players, same nights, same board, real two-sided
# prices. If the "other" column is near zero, the second leg is not a second edge and taking both
# is not leverage on a good bet - it is one good bet plus one coin flip.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260819)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
SIGS = ("flip", "hotover", "overshoot"); BET_MKTS = ("pra", "pr", "pts")

tip_on, gof = {}, {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    tip_on[(hm, d2)] = t2; tip_on[(aw, d2)] = t2
    gof[(hm, t2)] = gid; gof[(aw, t2)] = gid

MS = {}
for r in load("graded_bets.csv"):
    if (r.get("result") or "").upper() not in ("WIN", "LOSS"): continue
    src, mk, pl = (r.get("src") or ""), (r.get("market") or ""), (r.get("player") or "").lower()
    if src not in SIGS or mk not in BET_MKTS: continue
    tm = teamof.get(pl)
    gt = tip_on.get((tm, r.get("date") or "")) if tm else None
    if not gt: continue
    now = pgrow.get((pl, gt)); sd = side.get((pl, mk, gt), {})
    if not now or "Over" not in sd: continue
    ln = sd["Over"][1]; pv = prevline.get((pl, mk, gt))
    if pv is None or ln - pv >= 0.5 or now[mk] == ln: continue
    MS.setdefault((pl, gt), set()).add(mk)

BET, OTH = [], []
for (pl, mk, gt), sd in side.items():
    if (pl, gt) not in MS or "Over" not in sd or "Under" not in sd: continue
    if abs(sd["Over"][1] - sd["Under"][1]) > 0.01: continue
    now = pgrow.get((pl, gt))
    if not now or mk not in now: continue
    ln = sd["Over"][1]
    if now[mk] == ln: continue
    tm = teamof.get(pl)
    row = dict(pl=pl, mk=mk, gt=gt, gid=gof[(tm, gt)], o_od=sd["Over"][2], u_od=sd["Under"][2],
               o_won=now[mk] > ln, u_won=now[mk] < ln,
               core=(mk in BET_MKTS))
    (BET if mk in MS[(pl, gt)] else OTH).append(row)

def sc(rows, wk, ok):
    n = len(rows); w = sum(1 for r in rows if r[wk])
    u = sum((r[ok]-1) if r[wk] else -1.0 for r in rows)
    return n, 100*w/n, u, 100*u/n
def gboot(rows, wk, ok, T=3000):
    bg = collections.defaultdict(list)
    for r in rows: bg[r["gid"]].append(r)
    k = list(bg); o = []
    for _ in range(T):
        g = [x for p in [random.choice(k) for _ in k] for x in bg[p]]
        o.append(100*sum((x[ok]-1) if x[wk] else -1.0 for x in g)/len(g))
    o.sort(); return o[int(T*.025)], o[int(T*.975)]
def show(rows, lbl, wk, ok, minn=20):
    if len(rows) < minn: print(f"  {lbl:<46} n={len(rows)} too few"); return
    n, h, u, ro = sc(rows, wk, ok); lo, hi = gboot(rows, wk, ok)
    print(f"  {lbl:<46} n={n:<5}{h:>6.1f}%{u:>+8.2f}u{ro:>+8.1f}%  95CI [{lo:+6.1f},{hi:+6.1f}]")

print("="*104)
print("  THE MARKET WE PICKED vs THE ONES WE DIDN'T - same player, same night")
print("="*104)
show(BET, "  the market Model S bet: OVER", "o_won", "o_od")
show(OTH, "  her OTHER markets: OVER",      "o_won", "o_od")
show(OTH, "  her OTHER markets: UNDER",     "u_won", "u_od")
print("")
print("  restricted to the three markets Model S is even allowed to bet:")
show([r for r in OTH if r["core"]], "  her other pra/pr/pts: OVER", "o_won", "o_od")
print("")
print("="*104)
print("  HER OTHER MARKETS, ONE BY ONE (over side)")
print("="*104)
for m in ("pts", "pr", "pra", "pa", "ra", "reb", "ast"):
    show([r for r in OTH if r["mk"] == m], f"    {m}", "o_won", "o_od")
print("")
print("  breakeven at the board's average price is about 53.8%. Read the hit rates against that,")
print("  not against 50% - the 7.4% margin is why a 52% side still loses money.")
