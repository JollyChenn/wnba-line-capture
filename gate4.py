# gate4.py - Thornton qualified on PTS 8.5 AND PR 13.5. Take one, or take both?
# ---------------------------------------------------------------------------------------------
# Gate 4 says one position per player, keep the best price. That throws away a bet that passed
# every other test, so it needs to justify itself. Three policies on the identical signal set:
#
#   KEEP BEST PRICE    what the card does now - highest decimal odds wins the slot
#   KEEP BEST CUSHION  keep the one furthest below her 10-game median instead
#   TAKE BOTH          no gate 4 at all, every qualifying position gets 1u
#
# There is a reason to doubt BEST PRICE. Higher odds is the book saying LESS LIKELY. Picking the
# longest price on a player is picking the position the book is most confident about, which is the
# opposite of what an overshoot signal is supposed to be exploiting. Cushion - how far the line
# sits below what she actually does - is the quantity the signal is built on.
#
# And there is a reason to doubt TAKE BOTH beyond its ROI: PR = PTS + REB. The two bets are not
# two opinions, they are one opinion wearing two lines. If she scores 9 and grabs 5, both land; if
# she has a quiet night, both die. Two units of the same risk is leverage, and the correlation
# section below measures exactly how much.
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
    gof[(hm, t2)] = gid; gof[(aw, t2)] = gid

def med_before(pl, mk, gt):
    """her 10-game median in this market, using ONLY games before this one"""
    v = [r[mk] for r in hist.get(pl, []) if r["tip"] < gt]
    return statistics.median(v[-10:]) if len(v) >= 3 else None

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
    md = med_before(pl, mk, gt)
    R.append(dict(pl=pl, mk=mk, gt=gt, gid=gof[(tm, gt)], date=r.get("date"), src=src,
                  ln=p_l, od=p_o, won=now[mk] > p_l, act=now[mk],
                  cush=(md - p_l) if md is not None else None))

grp = collections.defaultdict(list)
for r in R: grp[(r["pl"], r["gt"])].append(r)
multi = {k: v for k, v in grp.items() if len(v) > 1}
print(f"{len(R)} qualifying positions over {len(grp)} player-games")
print(f"  player-games with MORE THAN ONE qualifying market: {len(multi)}"
      f"  ({sum(len(v) for v in multi.values())} positions)")
print(f"  market pairs seen: " + ", ".join(
    f"{'+'.join(sorted(m['mk'] for m in v))}:{c}" for (v, c) in
    collections.Counter("+".join(sorted(m["mk"] for m in v)) for v in multi.values()).items()
    for v in [None]) if False else "")
pc = collections.Counter("+".join(sorted(m["mk"] for m in v)) for v in multi.values())
print("  which markets double up: " + ", ".join(f"{k} x{c}" for k, c in pc.most_common()))
print("")

def sc(rows):
    n = len(rows); w = sum(1 for r in rows if r["won"])
    u = sum((r["od"]-1) if r["won"] else -1.0 for r in rows)
    return n, 100*w/n, u, 100*u/n
def gboot(rows, T=3000):
    bg = collections.defaultdict(list)
    for r in rows: bg[r["gid"]].append(r)
    k = list(bg); o = []
    for _ in range(T):
        g = [x for p in [random.choice(k) for _ in k] for x in bg[p]]
        o.append(100*sum((x["od"]-1) if x["won"] else -1.0 for x in g)/len(g))
    o.sort(); return o[int(T*.025)], o[int(T*.975)]
def show(rows, lbl, minn=10):
    if len(rows) < minn: print(f"  {lbl:<44} n={len(rows)} too few"); return
    n, h, u, ro = sc(rows); lo, hi = gboot(rows)
    print(f"  {lbl:<44} risk {n:>3}u{h:>7.1f}%{u:>+8.2f}u{ro:>+8.1f}%  95CI [{lo:+6.1f},{hi:+6.1f}]")

byprice = [max(v, key=lambda r: r["od"]) for v in grp.values()]
withc = [v for v in grp.values() if all(r["cush"] is not None for r in v)]
bycush = [max(v, key=lambda r: r["cush"]) for v in withc]
bycush_pricetwin = [max(v, key=lambda r: r["od"]) for v in withc]
allpos = R

print("="*104)
print("  THE THREE POLICIES")
print("="*104)
show(byprice, "  gate 4 ON, keep BEST PRICE  (the card today)")
show(allpos,  "  gate 4 OFF, TAKE BOTH")
print("")
print("  like-for-like on the player-games where a median exists for every position:")
show(bycush_pricetwin, "    keep best PRICE")
show(bycush,           "    keep best CUSHION")
print("")
print("="*104)
print("  THE DISCARDED BETS - what gate 4 actually throws away")
print("="*104)
kept = {id(r) for r in byprice}
disc = [r for r in R if id(r) not in kept]
show(disc, "  the positions gate 4 removes")
show([r for r in byprice if (r["pl"], r["gt"]) in multi], "  the ones it keeps, on those same nights")
print("")
print("="*104)
print("  CORRELATION - is the second bet a second opinion, or the same one twice?")
print("="*104)
pairs = []
for k, v in multi.items():
    for i in range(len(v)):
        for j in range(i+1, len(v)):
            pairs.append((v[i], v[j]))
if len(pairs) >= 6:
    p = sum(1 for r in R if r["won"]) / len(R)
    both = sum(1 for a, b in pairs if a["won"] and b["won"])
    neither = sum(1 for a, b in pairs if not a["won"] and not b["won"])
    split = len(pairs) - both - neither
    print(f"  {len(pairs)} same-player pairs   both win {both}  both lose {neither}  split {split}")
    print(f"  both win {100*both/len(pairs):.1f}%   independence would say {100*p*p:.1f}%")
    print(f"  they AGREE {100*(both+neither)/len(pairs):.1f}% of the time (50% = unrelated)")
else:
    print(f"  only {len(pairs)} same-player pairs - too few to measure correlation")
print("")
print("="*104)
print("  WHAT IT MEANS FOR TONIGHT")
print("="*104)
print("  PR = PTS + REB. Thornton PTS over 8.5 needs 9 points. PR over 13.5 needs those 9 plus")
print("  5 rebounds. The second bet is the first bet AND a rebound bet, at a shorter price.")
print("  Doubling a correlated position doubles the good nights and the bad ones together -")
print("  it does not spread risk, it concentrates it on one player's evening.")
