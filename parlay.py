# parlay.py - the card pairs bets off at the straight product. When both legs are in the SAME
# GAME, is that product the right price?
# ---------------------------------------------------------------------------------------------
# model_card.py:296 justifies the parlay line by noting 1xbet pays the exact product, so a pair
# breaks even at the same p as a single and is "pure leverage". That is true ONLY IF THE LEGS ARE
# INDEPENDENT. Last night the card paired Reese (ATL) with Young (LV) - the same 40 minutes of
# basketball. Two overs on one game are not independent:
#
#   * a fast, high-possession game lifts BOTH scoring lines
#   * a grinding low-possession game sinks BOTH
#   * a blowout empties the fourth quarter for BOTH benches
#
# If P(both win) > p1*p2, then a parlay priced at p1*p2 is UNDERPRICED and the pair is worth more
# than the two singles. If the correlation runs the other way - one team's over feeding off the
# other's under, usage cannibalised between teammates - the product OVERPRICES it and the parlay
# is a trap dressed as leverage.
#
# So: measure P(both win) directly on every same-game pair Model S has produced, and compare it
# to the independence benchmark. Split TEAMMATES from OPPOSING sides, because they should differ:
# teammates share possessions (they can cannibalise each other), opponents share only pace.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260819)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
SIGS = ("flip", "hotover", "overshoot"); BET_MKTS = ("pra", "pr", "pts")

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
tip_on, gof = {}, {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    tip_on[(hm, d2)] = t2; tip_on[(aw, d2)] = t2
    gof[(hm, t2)] = (gid, d2); gof[(aw, t2)] = (gid, d2)

R = []
for r in load("graded_bets.csv"):
    if (r.get("result") or "").upper() not in ("WIN", "LOSS"): continue
    src, mk, pl = (r.get("src") or ""), (r.get("market") or ""), (r.get("player") or "").lower()
    if src not in SIGS or mk not in BET_MKTS: continue
    tm = teamof.get(pl)
    gt = tip_on.get((tm, r.get("date") or "")) if tm else None
    if not gt: continue
    q = seq.get((pl, mk, gt), []); now = pgrow.get((pl, gt))
    if len(q) < 2 or not now: continue
    pv = prevline.get((pl, mk, gt))
    if pv is None: continue
    p_t, p_l, p_o = q[-1]
    if p_l - pv >= 0.5 or now[mk] == p_l: continue
    gid, dt = gof[(tm, gt)]
    R.append(dict(pl=pl, mk=mk, gt=gt, gid=gid, date=dt, tm=tm, od=p_o, won=now[mk] > p_l))
best = {}
for r in sorted(R, key=lambda x: -x["od"]): best.setdefault((r["pl"], r["gt"]), r)
R = list(best.values())
p = sum(1 for r in R if r["won"]) / len(R)
bg = collections.defaultdict(list)
for r in R: bg[r["gid"]].append(r)
print(f"MODEL S: {len(R)} bets, single-leg win rate p = {p:.3f}")
print(f"  games carrying 2+ bets: {sum(1 for v in bg.values() if len(v) >= 2)}")
print("")

def pairs(sel):
    out = []
    for g, rows in bg.items():
        for i in range(len(rows)):
            for j in range(i+1, len(rows)):
                a, b = rows[i], rows[j]
                if sel(a, b): out.append((a, b))
    return out

print("="*104)
print("  DOES A SAME-GAME PAIR WIN TOGETHER MORE OFTEN THAN CHANCE?")
print("="*104)
print(f"  independence benchmark: p * p = {100*p*p:.1f}%   (both legs land, if unrelated)")
print("")
for lbl, sel in (("all same-game pairs", lambda a, b: True),
                 ("  TEAMMATES", lambda a, b: a["tm"] == b["tm"]),
                 ("  OPPOSING sides", lambda a, b: a["tm"] != b["tm"])):
    P = pairs(sel)
    if len(P) < 6:
        print(f"  {lbl:<24}{len(P)} pairs - too few"); continue
    both = sum(1 for a, b in P if a["won"] and b["won"])
    obs = both / len(P)
    se = math.sqrt(max(obs*(1-obs), 1e-9)/len(P))
    tot = sum((a["od"]*b["od"]-1) if (a["won"] and b["won"]) else -1.0 for a, b in P)
    print(f"  {lbl:<24}{len(P):>3} pairs   both win {100*obs:5.1f}% +/-{100*1.96*se:4.1f}"
          f"   vs {100*p*p:5.1f}%   lift {100*(obs-p*p):+5.1f}pp")
    print(f"  {'':<24}    parlay at the product: {tot:+6.2f}u on {len(P)} bets = ROI {100*tot/len(P):+6.1f}%")
print("")

# a proper null: keep each game's SIZE, but draw its members' outcomes from the pool at random.
# that destroys any within-game linkage while preserving the overall win rate and game structure.
P = pairs(lambda a, b: True)
real = sum(1 for a, b in P if a["won"] and b["won"]) / len(P) if P else 0
pool = [r["won"] for r in R]
T = 8000; beat = 0
for _ in range(T):
    shuf = pool[:]; random.shuffle(shuf)
    it = iter(shuf); sim = {}
    for g, rows in bg.items(): sim[g] = [next(it) for _ in rows]
    tot = c = 0
    for g, w in sim.items():
        for i in range(len(w)):
            for j in range(i+1, len(w)):
                c += 1; tot += 1 if (w[i] and w[j]) else 0
    if c and tot/c >= real: beat += 1
print("="*104)
print("  NULL: same games, same sizes, outcomes reshuffled across the whole pool")
print("="*104)
print(f"  observed both-win rate {100*real:.1f}%   p = {beat/T:.4f}")
print("")
print("  a small p means same-game legs really do land together more than chance, which would make")
print("  a parlay priced at the straight product CHEAP. a large p means the card's 'pure leverage'")
print("  description is the correct one and the pair adds variance without adding value.")
print("")
print("="*104)
print("  SINGLES vs SINGLES+PAIRS, on the same picks")
print("="*104)
u1 = sum((r["od"]-1) if r["won"] else -1.0 for r in R)
print(f"  singles only            risk {len(R):>3}u   {u1:+7.2f}u   ROI {100*u1/len(R):+6.1f}%")
tot = sum((a["od"]*b["od"]-1) if (a["won"] and b["won"]) else -1.0 for a, b in P)
print(f"  pairs only              risk {len(P):>3}u   {tot:+7.2f}u   ROI {100*tot/len(P):+6.1f}%")
print(f"  both layers             risk {len(R)+len(P):>3}u   {u1+tot:+7.2f}u   ROI {100*(u1+tot)/(len(R)+len(P)):+6.1f}%")
print("")
print("  NOTE: the card pairs CONSECUTIVE picks by tip, no reuse, so it forms fewer pairs than the")
print("  all-pairs count above. This is the ceiling of the pair layer, not what the card offered.")
