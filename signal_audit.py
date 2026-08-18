# signal_audit.py - the decisive one. Is the ENGINE'S SIGNAL real, or only the star?
# ---------------------------------------------------------------------------------------------
# passcount.py showed the star filter alone, deduped, across the whole board returns -4.4%. So
# the +11% headline cannot be coming from the star - it has to be coming from flip / hotover /
# overshoot choosing WHICH players to look at. That has never been tested on its own with a null
# that respects clustering, and everything else this week collapsed once it was.
#
# The comparison that matters is not "is Model S positive". It is:
#
#     Model S   vs   the same star filter applied to every board quote it did NOT pick
#
# If the signals carry information, the picked group beats the unpicked group. If they do not,
# Model S is 838 unraised quotes with extra steps and its +11% is a small-sample accident.
#
# Every interval is a PLAYER-BLOCK bootstrap, and the permutation shuffles the src label between
# PLAYERS rather than between bets, for the reason recorded in MODEL.md's method note.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260919)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
BET_MKTS = ("pra", "pr", "pts"); SIGS = ("flip", "hotover", "overshoot")

# ---- which (player, market, game) did the engine actually flag, and with which signal? ----------
flag = {}
for b in sorted(load("bets_log.csv"), key=lambda r: r.get("captured_utc") or ""):
    if b.get("side") != "Over": continue
    src = b.get("src") or "?"
    pl, mk = (b.get("player") or "").lower(), b.get("market")
    t0 = ts(b.get("captured_utc")); tm = teamof.get(pl)
    if not (t0 and tm): continue
    gt = game_for(tm, t0)
    if gt: flag.setdefault((pl, mk, gt), src)

IDX = {(r["pl"], r["mk"], r["gt"]): r for r in B}
for r in B: r["src"] = flag.get((r["pl"], r["mk"], r["gt"]))
U = [r for r in B if r["mk"] in BET_MKTS and r.get("starred") is True]   # star-filtered universe
def dedupe(rows):
    best = {}
    for r in sorted(rows, key=lambda x: -x["over_od"]): best.setdefault((r["pl"], r["gt"]), r)
    return sorted(best.values(), key=lambda r: (r["date"], r["pl"]))

def roi(rows): return 100*sum((r["over_od"]-1) if r["over_won"] else -1.0 for r in rows)/len(rows) if rows else 0.0
def hit(rows): return 100*sum(1 for r in rows if r["over_won"])/len(rows) if rows else 0.0
def pboot(rows, T=3000):
    bp = collections.defaultdict(list)
    for r in rows: bp[r["pl"]].append(r)
    keys = list(bp)
    if len(keys) < 8: return None, None
    out = []
    for _ in range(T):
        pick = [random.choice(keys) for _ in keys]
        out.append(roi([r for p in pick for r in bp[p]]))
    out.sort()
    return out[int(T*.025)], out[int(T*.975)]
def show(rows, label, minn=25):
    n = len(rows)
    if n < minn:
        print(f"  {label:<46} n={n:<5} too few"); return
    lo, hi = pboot(rows)
    ci = f"[{lo:+6.1f}%,{hi:+6.1f}%]" if lo is not None else "       -        "
    print(f"  {label:<46} n={n:<5} {len({r['pl'] for r in rows}):>3}pl  {hit(rows):5.1f}%  "
          f"ROI {roi(rows):+6.1f}%  95CI {ci}")

cov = sum(1 for r in U if r.get("src"))
print(f"{len(B)} board quotes | {len(U)} star-filtered in BET_MKTS | {cov} carry an engine src")
print("")
print("="*112)
print("  1. THE COMPARISON THAT DECIDES IT")
print("="*112)
print("  same star filter, same markets, same dedup. only difference: did a signal fire?")
print("")
S    = dedupe([r for r in U if r.get("src") in SIGS])
NOTS = dedupe([r for r in U if r.get("src") not in SIGS])
show(S,    "  MODEL S  (signal fired)")
show(NOTS, "  same filter, NO signal fired")
show(dedupe(U), "  everything star-filtered (both groups)")
print("")
d = roi(S) - roi(NOTS)
print(f"  gap: {d:+.1f} percentage points in Model S's favour")
print("")
print("="*112)
print("  2. PER SIGNAL - which of the three is carrying it?")
print("="*112)
for s in SIGS:
    show(dedupe([r for r in U if r.get("src") == s]), f"  {s}")
print("")
print("  and the same signals WITHOUT the star, to see what the star is worth on each:")
for s in SIGS:
    g = dedupe([r for r in B if r["mk"] in BET_MKTS and r.get("src") == s])
    show(g, f"  {s}, no star filter")
print("")
print("="*112)
print("  3. OUT OF SAMPLE")
print("="*112)
dts = sorted({r["date"] for r in U}); cut = dts[int(len(dts)*0.6)]
print(f"  split {cut}")
for lbl, g in (("MODEL S", S), ("no signal", NOTS)):
    show([r for r in g if r["date"] <  cut], f"    {lbl}  IN ")
    show([r for r in g if r["date"] >= cut], f"    {lbl}  OUT")
    print("")
print("="*112)
print("  4. PERMUTATION - shuffle the src label between PLAYERS")
print("="*112)
print("  a player keeps her whole season and every outcome in it; only the question of whether")
print("  the engine liked her moves. that asks: given these players, is picking THESE ones better")
print("  than picking a random group of the same size?")
print("")
bp = collections.defaultdict(list)
for r in dedupe(U): bp[r["pl"]].append(r)
players = list(bp)
sig_pl = {r["pl"] for r in S}
k = len(sig_pl)
real = roi([r for p in sig_pl for r in bp.get(p, [])])
T = 4000; beat = 0; sims = []
for _ in range(T):
    pick = set(random.sample(players, k))
    v = roi([r for p in pick for r in bp[p]])
    sims.append(v)
    if v >= real: beat += 1
sims.sort()
print(f"  Model S players ({k} of {len(players)}): {real:+.1f}%")
print(f"  random same-size groups: median {sims[T//2]:+.1f}%  p95 {sims[int(T*.95)]:+.1f}%  max {sims[-1]:+.1f}%")
print(f"  PLAYER-BLOCK p = {beat/T:.4f}")
print("")
print("="*112)
print("  5. THE FORWARD RECORD - the only part not fitted to anything")
print("="*112)
fw = [r for r in load("graded_bets.csv") if (r.get("result") or "") in ("W", "L")]
if fw:
    w = sum(1 for r in fw if r["result"] == "W")
    u = 0.0
    for r in fw:
        o = f(r.get("odds")) or 0
        u += (o-1) if r["result"] == "W" else -1.0
    print(f"  graded forward bets: n={len(fw)}  {w}W-{len(fw)-w}L  {100*w/len(fw):.1f}%  "
          f"{u:+.2f}u  ROI {100*u/len(fw):+.1f}%")
    need = 50
    print(f"  at n={len(fw)}, a 55% true rate and a 50% true rate are indistinguishable.")
    print(f"  {max(0, need-len(fw))} more graded bets before the record can say anything at all.")
else:
    print("  none graded yet")
