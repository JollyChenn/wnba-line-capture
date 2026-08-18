# signal_audit2.py - the sharp version of the question signal_audit.py asked bluntly.
# ---------------------------------------------------------------------------------------------
# signal_audit's permutation shuffled the src label BETWEEN players. That tests whether the
# engine picks good PLAYERS, which is not what it claims to do - it claims to pick good NIGHTS.
# A player-level null is passed by any rule that happens to like productive players, and it
# returned +1.1% against a +1.3% p95 ceiling, which is nearly a tie on a question we did not ask.
#
# The right null holds the player FIXED and moves the timing: for each player, draw at random the
# same number of her star-filtered games that the engine actually flagged. If the signals carry
# nothing beyond "these are decent players", picking her games at random scores the same.
#
# Also fixes the forward read - graded_bets.csv stores WIN/loss, not W/L, so the earlier run
# reported "none graded" on a file holding 869 settled rows.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260920)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "signal_audit.py"), encoding="utf-8").read()
     .split('cov = sum(1 for r in U if r.get("src"))')[0])

S    = dedupe([r for r in U if r.get("src") in SIGS])
Ud   = dedupe(U)
bp   = collections.defaultdict(list)
for r in Ud: bp[r["pl"]].append(r)
picked = collections.Counter(r["pl"] for r in S)
print(f"{len(S)} Model S bets over {len(picked)} players | {len(Ud)} star-filtered quotes available")
print("")
print("="*108)
print("  1. WITHIN-PLAYER PERMUTATION - same players, same bet counts, random NIGHTS")
print("="*108)
elig = {p: c for p, c in picked.items() if len(bp.get(p, [])) > c}
print(f"  {len(elig)} of {len(picked)} players have more star-filtered games than the engine flagged")
print(f"  (the rest offer no alternative nights, so their bets are held fixed in every draw)")
print("")
def draw():
    out = []
    for p, c in picked.items():
        pool = bp.get(p, [])
        out.extend(random.sample(pool, c) if len(pool) > c else pool)
    return out
real = roi(S)
T = 5000; beat = 0; sims = []
for _ in range(T):
    v = roi(draw()); sims.append(v)
    if v >= real: beat += 1
sims.sort()
print(f"  MODEL S actual nights: {real:+.1f}%  ({hit(S):.1f}%)")
print(f"  random nights, same players & counts: median {sims[T//2]:+.1f}%  "
      f"p95 {sims[int(T*.95)]:+.1f}%  max {sims[-1]:+.1f}%")
print(f"  WITHIN-PLAYER p = {beat/T:.4f}")
print("")
print("  this is the number that says whether the SIGNAL means anything. the star filter is")
print("  already applied to both sides, and the player mix is identical by construction.")
print("")
print("="*108)
print("  2. COVERAGE CAVEAT - is the control group fair?")
print("="*108)
print("  bets_log only records flagged bets, so 'no signal fired' also contains quotes the engine")
print("  never SAW. if it started mid-season or scans a narrow window, that group is polluted with")
print("  games it was never offered.")
print("")
bydate_s = collections.Counter(r["date"] for r in S)
bydate_u = collections.Counter(r["date"] for r in Ud)
ds = sorted(bydate_u)
cover = [d for d in ds if bydate_s.get(d, 0) > 0]
print(f"  star-filtered quotes span {ds[0]} to {ds[-1]} over {len(ds)} dates")
print(f"  the engine flagged something on {len(cover)} of them ({100*len(cover)/len(ds):.0f}%)")
print("")
Uc = [r for r in Ud if r["date"] in set(cover)]
Sc = [r for r in S  if r["date"] in set(cover)]
Nc = [r for r in Uc if r.get("src") not in SIGS]
print("  restricting BOTH groups to dates the engine demonstrably ran:")
show(Sc, "    MODEL S")
show(Nc, "    no signal fired, same dates")
print("")
print("="*108)
print("  3. THE FORWARD RECORD - reading the right result codes this time")
print("="*108)
def read(fn, lbl):
    rows = [r for r in load(fn) if (r.get("result") or "").upper() in ("WIN", "LOSS")]
    if not rows:
        print(f"  {lbl:<26} nothing settled"); return
    w = sum(1 for r in rows if r["result"].upper() == "WIN")
    u = 0.0
    for r in rows:
        o = f(r.get("odds")) or 0
        u += (o-1) if r["result"].upper() == "WIN" else -1.0
    print(f"  {lbl:<26} n={len(rows):<4} {w}W-{len(rows)-w}L  {100*w/len(rows):5.1f}%  "
          f"{u:+6.2f}u  ROI {100*u/len(rows):+6.1f}%")
read("model_forward.csv", "MODEL S forward")
read("graded_bets.csv", "graded_bets (all srcs)")
gb = [r for r in load("graded_bets.csv") if (r.get("result") or "").upper() in ("WIN", "LOSS")]
print("")
print("  graded_bets is the WHOLE menu the engine ever pinged, not Model S. by src:")
for s in sorted({(r.get("src") or "?") for r in gb}):
    rows = [r for r in gb if (r.get("src") or "?") == s]
    if len(rows) < 15: continue
    w = sum(1 for r in rows if r["result"].upper() == "WIN")
    u = sum(((f(r.get("odds")) or 0)-1) if r["result"].upper() == "WIN" else -1.0 for r in rows)
    print(f"    {s:<24} n={len(rows):<4} {100*w/len(rows):5.1f}%  {u:+7.2f}u  ROI {100*u/len(rows):+6.1f}%")
print("")
mf = [r for r in load("model_forward.csv") if (r.get("result") or "").upper() in ("WIN", "LOSS")]
n = len(mf)
if n:
    print(f"  POWER: at n={n}, the 95% interval on a 50% coin is roughly "
          f"+/-{100*1.96*0.5/math.sqrt(n):.0f} percentage points.")
    print(f"  a true 55% edge and a true 50% coin are not separable until roughly n=250.")
