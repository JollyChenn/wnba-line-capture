# rank2_probe.py - the second option's OVER was the only positive cell. Chase it properly.
# ---------------------------------------------------------------------------------------------
# From the full-board sweep: the team's SECOND-best scorer's over returns +2.8% on n=1475, the
# only positive cell among 22, global p=0.078. Everything else on that board loses.
#
# It also has the right mechanism for this project. The book prices the STAR carefully because
# everyone bets her; the second option gets less attention. That is the same inattention story
# the star filter exploits, pointed at a different axis.
#
# Against it: the pattern is NOT monotonic - rank1 -4.3%, rank2 +2.8%, rank3-4 -10.7%, rank5+
# -8.6%. A spike at one rank is the shape noise makes. So this needs the full treatment.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260912)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "under_and_role.py"), encoding="utf-8").read().split('print(f"{len(B)} player-market-games')[0])

def cell(rows, which="over"):
    n = len(rows)
    if not n: return 0, 0, 0, 0
    if which == "over":
        w = sum(1 for r in rows if r["over_won"])
        u = sum((r["over_od"]-1) if r["over_won"] else -1.0 for r in rows)
        be = 100/(sum(r["over_od"] for r in rows)/n)
    else:
        w = sum(1 for r in rows if not r["over_won"])
        u = sum((r["under_od"]-1) if not r["over_won"] else -1.0 for r in rows)
        be = 100/(sum(r["under_od"] for r in rows)/n)
    return n, 100*w/n, 100*u/n, be
def show(rows, label, which="over", minn=60):
    n, h, r_, be = cell(rows, which)
    if n < minn:
        print(f"  {label:<44} n={n:<5} too few"); return
    print(f"  {label:<44} n={n:<5} {h:5.1f}%  ROI {r_:+6.1f}%  be {be:.1f}%")

print(f"{len(B)} two-sided quotes")
dates = sorted({pgrow[(r['pl'], r['gt'])]['date'] for r in B})
cut = dates[int(len(dates)*0.6)]
for r in B: r["date"] = pgrow[(r["pl"], r["gt"])]["date"]
print("")
print("="*100)
print("  IS IT MONOTONIC IN RANK, OR A SPIKE AT 2?")
print("="*100)
for k in range(1, 8):
    show([r for r in B if r["rank"] == k], f"  rank {k} over", minn=40)
print("")
print("="*100)
print("  OUT OF SAMPLE  (split " + cut + ")")
print("="*100)
r2 = [r for r in B if r["rank"] == 2]
show([r for r in r2 if r["date"] <  cut], "  rank2 over  IN")
show([r for r in r2 if r["date"] >= cut], "  rank2 over  OUT")
print("")
for lbl, k in (("rank1", 1), ("rank3-4", None)):
    g = [r for r in B if (r["rank"] == 1 if k else 3 <= r["rank"] <= 4)]
    show([r for r in g if r["date"] <  cut], f"  {lbl} over  IN")
    show([r for r in g if r["date"] >= cut], f"  {lbl} over  OUT")
print("")
print("="*100)
print("  BY MARKET - is rank2 positive everywhere, or carried by one market?")
print("="*100)
for mk in ALL_MK:
    show([r for r in r2 if r["mk"] == mk], f"  rank2 {mk}", minn=50)
print("")
print("="*100)
print("  DOES IT OVERLAP WITH MODEL S? (if our picks ARE rank2, this is not a new signal)")
print("="*100)
rk = collections.Counter(r["rank"] for r in B)
print("  rank distribution of ALL board quotes: " +
      ", ".join(f"{k}:{v}" for k, v in sorted(rk.items()) if k < 8))
SIGS = ("flip", "hotover", "overshoot")
ours = set()
for b in load("bets_log.csv"):
    if b.get("side") == "Over" and b.get("src") in SIGS:
        ours.add((b.get("player") or "").lower())
og = [r for r in B if r["pl"] in ours]
print(f"  quotes on players our engine has ever flagged: {len(og)}")
print("  their rank distribution: " +
      ", ".join(f"{k}:{v}" for k, v in sorted(collections.Counter(r['rank'] for r in og).items()) if k < 8))
print("")
show([r for r in r2 if r["pl"] in ours], "  rank2 AND ever-flagged")
show([r for r in r2 if r["pl"] not in ours], "  rank2, never flagged")
