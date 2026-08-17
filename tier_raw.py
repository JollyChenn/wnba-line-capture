# tier_raw.py - include the RAW bets and tier the stakes? The per-signal table argues for it.
# ---------------------------------------------------------------------------------------------
# What the replication test actually showed is that the star does NOT mean the same thing in
# every signal:
#     flip       starred +17.9%   raised -13.1%    <- the star is a GATE here
#     hotover    starred +47.1%   raised -13.6%    <- same
#     overshoot  starred  +6.4%   raised  +4.8%    <- the star does almost nothing; BOTH playable
# That is a structural observation, not a fitted threshold, and it suggests a rule shaped like:
#     flip/hotover  -> star REQUIRED, and they carry the edge, so stake more
#     overshoot     -> star irrelevant, both halves mildly positive, so stake less and take both
#
# HEALTH WARNING, stated before the numbers rather than after: this scheme was designed by
# looking at that table. It is fitted. The honest test is not whether it beats flat staking
# in-sample - it will, by construction - but whether it survives the split and the control.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260905)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "star_replicate.py"), encoding="utf-8").read()
     .split('def roi(rows): return')[0])

def roi(rows, stake=lambda r: 1.0):
    risk = sum(stake(r) for r in rows)
    prof = sum(stake(r)*((r["odds"]-1) if r["won"] else -1.0) for r in rows)
    return risk, prof, (prof/risk if risk else 0.0)
def dd_of(rows, stake):
    eq = peak = dd = 0.0
    for r in rows:
        eq += stake(r)*((r["odds"]-1) if r["won"] else -1.0)
        peak = max(peak, eq); dd = min(dd, eq-peak)
    return dd

FH = ("flip", "hotover")
SCHEMES = [
    ("LIVE   starred only, flat 1u",
     [r for r in ALL if r["star"]], lambda r: 1.0),
    ("A      starred only, flip/hot 2u, over 1u",
     [r for r in ALL if r["star"]],
     lambda r: 2.0 if r["src"] in FH else 1.0),
    ("B      + overshoot RAISED at 1u",
     [r for r in ALL if r["star"] or r["src"] == "overshoot"],
     lambda r: 2.0 if (r["src"] in FH and r["star"]) else 1.0),
    ("C      + overshoot RAISED at 0.5u",
     [r for r in ALL if r["star"] or r["src"] == "overshoot"],
     lambda r: 2.0 if (r["src"] in FH and r["star"]) else (0.5 if not r["star"] else 1.0)),
    ("D      EVERYTHING, tiered (your proposal)",
     ALL,
     lambda r: 2.0 if (r["src"] in FH and r["star"]) else (0.5 if not r["star"] else 1.0)),
    ("E      EVERYTHING, flat 1u",
     ALL, lambda r: 1.0),
]
print("="*112)
print(f"  {len(ALL)} candidates: {sum(1 for r in ALL if r['star'])} starred, "
      f"{sum(1 for r in ALL if not r['star'])} raised")
print("="*112)
print(f"  {'scheme':<44}{'bets':>6}{'risk':>9}{'profit':>10}{'ROI':>9}{'worst DD':>11}")
base = None
for lbl, rows, stake in SCHEMES:
    risk, prof, r_ = roi(rows, stake)
    d = dd_of(rows, stake)
    if base is None: base = (risk, prof)
    print(f"  {lbl:<44}{len(rows):>6}{risk:>8.1f}u{prof:>+9.2f}u{100*r_:>+8.1f}%{d:>+10.2f}u")
print("")
print("="*112)
print("  EQUAL RISK - scale each to deploy the same capital as the live scheme")
print("="*112)
target = base[0]
for lbl, rows, stake in SCHEMES:
    risk, prof, r_ = roi(rows, stake)
    sc = target/risk
    print(f"  {lbl:<44} stake x{sc:.2f}   profit {prof*sc:+7.2f}u   DD {dd_of(rows,stake)*sc:+7.2f}u")
print("")
print("="*112)
print("  OUT OF SAMPLE - the test that decides whether this is structure or fitting")
print("="*112)
dts = sorted({r["date"] for r in ALL}); cut = dts[int(len(dts)*0.6)]
print(f"  split at {cut}")
print(f"  {'scheme':<44}{'IN ROI':>10}{'OUT ROI':>10}{'drop':>9}")
for lbl, rows, stake in SCHEMES:
    a = [r for r in rows if r["date"] < cut]; b = [r for r in rows if r["date"] >= cut]
    if len(a) < 20 or len(b) < 20:
        print(f"  {lbl:<44} too few"); continue
    _, _, ra = roi(a, stake); _, _, rb = roi(b, stake)
    print(f"  {lbl:<44}{100*ra:>+9.1f}%{100*rb:>+9.1f}%{100*(rb-ra):>+8.1f}pp")
print("")
print("="*112)
print("  CONTROL - does the TIERING itself do anything, or is it the selection?")
print("  Shuffle which bets get the 2u tag, keeping counts and outcomes fixed.")
print("="*112)
rows = [r for r in ALL if r["star"]]
real_risk, real_prof, real_roi = roi(rows, lambda r: 2.0 if r["src"] in FH else 1.0)
nbig = sum(1 for r in rows if r["src"] in FH)
sims = []
for _ in range(20000):
    tag = set(random.sample(range(len(rows)), nbig))
    st = lambda i: 2.0 if i in tag else 1.0
    risk = sum(st(i) for i in range(len(rows)))
    prof = sum(st(i)*((rows[i]["odds"]-1) if rows[i]["won"] else -1.0) for i in range(len(rows)))
    sims.append(prof/risk)
sims.sort()
beat = sum(1 for x in sims if x >= real_roi)
print(f"  real tiered ROI {100*real_roi:+.1f}%   random 2u-tagging: median {100*sims[10000]:+.1f}%"
      f"  p95 {100*sims[19000]:+.1f}%   p = {beat/20000:.4f}")
