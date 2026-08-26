import os,sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import os as _o; sys.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))))
from _boot import ROOT, _src
random_seed_note = 1
exec(_src)
random.seed(20260826)

rows = load("xbet_board.csv")
print("board rows", len(rows))

# 1) at a single scrape instant, how many DISTINCT lines per (player, market)?
inst = collections.defaultdict(lambda: collections.defaultdict(dict))  # (pl,mk,t) -> line -> side->odds
for b in rows:
    t, o, ln = b.get("captured_utc"), f(b.get("odds")), f(b.get("line"))
    if not (t and o and ln is not None and b.get("market") in ALL_MK): continue
    inst[(_pl(b.get("player")), b.get("market"), t)][ln][b.get("side")] = o

nl = collections.Counter(len(v) for v in inst.values())
print("\nDISTINCT LINES per (player,market) AT ONE SCRAPE INSTANT:")
tot = sum(nl.values())
for k in sorted(nl): print(f"  {k} line(s): {nl[k]:>6}  ({100*nl[k]/tot:.2f}%)")

# two-sided rungs only
nl2 = collections.Counter(sum(1 for ln,s in v.items() if "Over" in s and "Under" in s) for v in inst.values())
print("\nDISTINCT TWO-SIDED rungs at one instant:")
for k in sorted(nl2): print(f"  {k}: {nl2[k]:>6} ({100*nl2[k]/tot:.2f}%)")

# 2) across a game (all scrapes for that player-market-game): distinct lines
pmg = collections.defaultdict(set)
pmg_t = collections.defaultdict(list)
for (pl, mk, t), v in inst.items():
    tm = teamof.get(pl)
    if not tm: continue
    tt = ts(t)
    g2 = game_for(tm, tt)
    if not g2: continue
    for ln in v: pmg[(pl, mk, g2)].add(ln)
    pmg_t[(pl, mk, g2)].append((tt, sorted(v)))
c = collections.Counter(len(v) for v in pmg.values())
tot2 = sum(c.values())
print(f"\nDISTINCT LINES per player-market-GAME (across all scrapes), n={tot2}:")
for k in sorted(c): print(f"  {k}: {c[k]:>6} ({100*c[k]/tot2:.2f}%)")
print(f"  >1 line: {100*sum(v for k,v in c.items() if k>1)/tot2:.2f}%   <-- the brief's 24.8%")

# 3) of those with >1 line across the game, how many EVER had 2 simultaneous?
multi_same_instant = 0; multi_over_time = 0
for k, lines in pmg.items():
    if len(lines) < 2: continue
    ever = any(len(v) > 1 for t, v in pmg_t[k])
    if ever: multi_same_instant += 1
    else: multi_over_time += 1
print(f"\nOf {multi_same_instant+multi_over_time} player-market-games with >1 line:")
print(f"  simultaneous (real ladder at some instant): {multi_same_instant}")
print(f"  sequential only (line MOVED, no ladder)   : {multi_over_time}")
