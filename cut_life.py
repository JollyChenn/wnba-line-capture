# cut_life.py - the RIGHT question: when the book CUTS a line (which is what creates our star),
# how long does that better number stay on the board before it reverts?
# ---------------------------------------------------------------------------------------------
# MY PREVIOUS ANALYSIS WAS BIASED AND I SHOULD SAY SO. I measured "time from first quote to first
# line move" and concluded lines are slow. But xbet_board.csv only records CHANGES against
# board_last.json, sampled at the capture cadence. A cut that appears and reverts BETWEEN two
# captures is never written down at all. So the data can only contain moves that survived long
# enough to be sampled - it is survivorship, and it cannot answer "are we missing fast ones".
# What it CAN answer is how long the cuts we DID catch stayed available.
import csv, os, sys, datetime, collections
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

MKTS = ("pra", "pr", "pts")
q = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, ln, o = ts(b.get("captured_utc")), f(b.get("line")), f(b.get("odds"))
    if t and ln is not None and o and b.get("market") in MKTS and b.get("side") == "Over":
        q[((b.get("player") or "").lower(), b.get("market"))].append((t, ln, o))

# how often do we actually capture? that sets the resolution of everything below
gaps = []
for k, v in q.items():
    v.sort()
    for a, b_ in zip(v, v[1:]):
        g = (b_[0]-a[0]).total_seconds()/60
        if 0 < g < 720: gaps.append(g)
gaps.sort()
print(f"OBSERVED CAPTURE GAPS between consecutive quotes on the same player-market ({len(gaps)} gaps)")
for pct in (10, 25, 50, 75, 90):
    print(f"   p{pct:<3} {gaps[int(len(gaps)*pct/100)]:7.0f} min")
print("   NOTE: the board logs only CHANGES, so these gaps are 'time until something changed',")
print("   not the scrape interval. A stable line produces no rows at all.")
print("")

cuts = []
for k, v in q.items():
    v.sort(); blocks, cur = [], [v[0]]
    for a, b_ in zip(v, v[1:]):
        if (b_[0]-a[0]).total_seconds() > 12*3600: blocks.append(cur); cur = []
        cur.append(b_)
    blocks.append(cur)
    for blk in blocks:
        for i in range(1, len(blk)):
            if blk[i][1] < blk[i-1][1]:                      # the book CUT the number
                lo = blk[i][1]
                back = next((blk[j][0] for j in range(i+1, len(blk)) if blk[j][1] > lo), None)
                life = (back - blk[i][0]).total_seconds()/60 if back else None
                cuts.append(dict(k=k, at=blk[i][0], frm=blk[i-1][1], to=lo,
                                 life=life, reverted=back is not None))
print("="*92)
print("  HOW LONG DOES A CUT LINE STAY ON THE BOARD?")
print("="*92)
rev = [c for c in cuts if c["reverted"]]
held = [c for c in cuts if not c["reverted"]]
print(f"  cuts observed          {len(cuts)}")
print(f"    reverted upward      {len(rev):>5}  ({100*len(rev)/len(cuts):4.1f}%)")
print(f"    stayed until tip     {len(held):>5}  ({100*len(held)/len(cuts):4.1f}%)  <- no rush on these")
print("")
if rev:
    L = sorted(c["life"] for c in rev)
    print("  for the ones that DID revert, how long the good number lasted:")
    for pct in (5, 10, 25, 50, 75, 90):
        print(f"    p{pct:<3} {L[int(len(L)*pct/100)]:8.0f} min")
    print("")
    print("  share of reverting cuts that would be GONE inside a given loop cadence:")
    for cad in (30, 20, 15, 10, 5):
        n = sum(1 for x in L if x <= cad)
        print(f"    loop every {cad:>2} min  ->  {n:>3}/{len(L)} = {100*n/len(L):4.1f}% could be missed entirely")
print("")
print("="*92)
print("  THE HONEST LIMIT OF THIS DATA")
print("="*92)
print("  Everything above is conditioned on us having CAPTURED the cut. Cuts that opened and")
print("  closed between two scrapes are absent from the file by construction. So this measures")
print("  'of the cuts we saw, how long they lasted' - it CANNOT measure how many we never saw.")
print("  The only way to answer that is to raise the capture rate and count what appears.")
