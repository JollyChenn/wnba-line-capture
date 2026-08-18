# reconcile.py - one funnel, every sample size explained, and the inconsistency between two of them.
import csv, os, sys, collections, datetime, statistics
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "gate5.py"), encoding="utf-8").read()
     .split('A = []')[0])
SIGS = ("flip", "hotover", "overshoot"); BET_MKTS = ("pra", "pr", "pts")

rows = [r for r in load("graded_bets.csv") if (r.get("result") or "").upper() in ("WIN", "LOSS")]
s12 = [r for r in rows if (r.get("src") or "") in SIGS and (r.get("market") or "") in BET_MKTS]
print("THE FUNNEL")
print("=" * 92)
print(f"  graded_bets settled                                     {len(rows)}")
print(f"  + gate 1 (src) + gate 2 (market)                        {len(s12)}")

both, openstar, pingstar = [], [], []
for r in s12:
    pl, mk = (r.get("player") or "").lower(), r.get("market")
    tm = teamof.get(pl)
    gt = None
    for gid, (d2, t2, hm, aw) in gmeta.items():
        if d2 == (r.get("date") or "") and tm in (hm, aw): gt = t2; break
    if not gt: continue
    q = seq.get((pl, mk, gt), [])
    if len(q) < 2: continue
    now = pgrow.get((pl, gt))
    if not now: continue
    o_ln = f(r.get("line")); p_ln = q[-1][1]
    if now[mk] == p_ln: continue
    pv = prevline.get((pl, mk, gt))
    both.append(r)
    if pv is not None and o_ln is not None and o_ln - pv < 0.5: openstar.append(r)
    if pv is not None and p_ln - pv < 0.5: pingstar.append(r)
print(f"  + has >=2 board quotes for that game (regradable)       {len(both)}   <- 51 lost here")
print("")
print("  NOW THE STAR - and this is where two of my numbers disagreed:")
print(f"    star judged on the OPENING line  (what I did first)   {len(openstar)}")
print(f"    star judged on the PING line     (what the card does) {len(pingstar)}")
print("")
so = {(r.get("player"), r.get("date"), r.get("market")) for r in openstar}
sp = {(r.get("player"), r.get("date"), r.get("market")) for r in pingstar}
print(f"    in BOTH: {len(so & sp)}   only-open: {len(so - sp)}   only-ping: {len(sp - so)}")
print("")
print("  model_card.py:202 uses line_now - the PING line. So the PING column is Model S.")
print("  My n=107 and n=93 judged the star on the OPENING line, which the card never sees.")
print("  That was wrong and the ping column supersedes them.")
print("")
print("=" * 92)
print("  SO THE ONE TRUE FUNNEL")
print("=" * 92)
print(f"  864  everything the engine logged")
print(f"  {len(s12):>4}  after gates 1+2 (the 3 signals, in pra/pr/pts)")
print(f"  {len(both):>4}  of those, regradable from the board archive")
print(f"  {len(pingstar):>4}  after gate 3, judged where the card judges it   = OLD MODEL S")
print(f"    55  after adding gate 5 (line not up since tonight opened)")
print(f"    13  that the card has actually pinged and that have settled")
