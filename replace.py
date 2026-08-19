# replace.py - recheck the drift rule, then try to SWAP a gate rather than stack one.
# ---------------------------------------------------------------------------------------------
# PART A - THE DRIFT RULE, RECHECKED.
# The dashboard buckets bets by dclv() = odds_clv, and reports drifted-against at -28% ROI. But
# odds_clv is OUR PRICE vs THE CLOSING PRICE. The closing price does not exist until the game is
# about to start. You cannot know it when you bet, and you cannot know it at ping time either.
#
# That is the same shape as the error basis_check.py found this morning: a rule evaluated with
# information from one moment, applied at another. The LIVE gate reads drift from the captures it
# has SO FAR, which is legitimate. The -28% headline is computed from the close, which is not. If
# the two disagree, the headline is describing a rule nobody can follow.
#
# So both are measured here, on identical bets:
#   CLOSING drift      odds_clv           retrospective, what the dashboard reports
#   PRE-TIP drift      last odds vs first odds on the board, knowable before tip
#
# PART B - REPLACE A GATE, DO NOT ADD ONE.
# Adding opponent-shade to Model S costs half the volume. The interesting question is whether it
# can do gate 3's JOB instead. Both are reprice-detectors: gate 3 asks "has the book already moved
# HER", shade asks "has the book already moved HER GAME". If they catch the same bets, one is
# redundant. If they catch different ones, swapping might hold ROI while keeping more volume.
# A full 2x2 on the gates 1+2 universe answers it - the diagonal is what matters.
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
tip_on, gof, oppof = {}, {}, {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    tip_on[(hm, d2)] = t2; tip_on[(aw, d2)] = t2
    gof[(hm, t2)] = gid; gof[(aw, t2)] = gid
    oppof[(hm, t2)] = aw; oppof[(aw, t2)] = hm
def med_before(pl, mk, gt):
    v = [r[mk] for r in hist.get(pl, []) if r["tip"] < gt]
    return statistics.median(v[-10:]) if len(v) >= 3 else None
shade = collections.defaultdict(list)
for (pl, mk, gt), sdq in side.items():
    if mk != "pts" or "Over" not in sdq: continue
    tm = teamof.get(pl)
    if not tm: continue
    m = med_before(pl, "pts", gt)
    if m is not None: shade[(tm, gt)].append(sdq["Over"][1] - m)

ALL = []
for r in load("graded_bets.csv"):
    if (r.get("result") or "").upper() not in ("WIN", "LOSS"): continue
    src, mk, pl = (r.get("src") or ""), (r.get("market") or ""), (r.get("player") or "").lower()
    tm = teamof.get(pl)
    gt = tip_on.get((tm, r.get("date") or "")) if tm else None
    if not gt: continue
    now = pgrow.get((pl, gt)); q = seq.get((pl, mk, gt), [])
    if not now or mk not in now or not q: continue
    p_t, p_l, p_o = q[-1]
    if now[mk] == p_l: continue
    pv = prevline.get((pl, mk, gt))
    op = oppof.get((tm, gt)); o_s = shade.get((op, gt), [])
    # PRE-TIP drift: how the price moved across the window we could actually watch.
    # odds going UP = the book lengthening us = money walking away.
    same = [x for x in q if abs(x[1] - p_l) < 0.01]           # same line only, else it is a line move
    pre = (p_o - same[0][2]) if len(same) >= 2 else None
    ALL.append(dict(pl=pl, mk=mk, gt=gt, gid=gof[(tm, gt)], date=r.get("date"), src=src, tm=tm,
                    ln=p_l, od=p_o, won=now[mk] > p_l, ret=((p_o-1) if now[mk] > p_l else -1.0),
                    g1=(src in SIGS), g2=(mk in BET_MKTS),
                    g3=(pv is not None and p_l - pv < 0.5),
                    clv=f(r.get("odds_clv")), pre=pre,
                    opp=(statistics.mean(o_s) if len(o_s) >= 3 else None)))
def dedupe(rows):
    best = {}
    for r in sorted(rows, key=lambda x: -x["od"]): best.setdefault((r["pl"], r["gt"]), r)
    return list(best.values())
def roi(rows): return 100*sum(r["ret"] for r in rows)/len(rows) if rows else 0.0
def sc(rows):
    n = len(rows); w = sum(1 for r in rows if r["won"])
    return n, 100*w/n, sum(r["ret"] for r in rows), roi(rows)
def gboot(rows, T=2500):
    bg = collections.defaultdict(list)
    for r in rows: bg[r["gid"]].append(r)
    k = list(bg); o = []
    for _ in range(T): o.append(roi([x for p in [random.choice(k) for _ in k] for x in bg[p]]))
    o.sort(); return o[int(T*.025)], o[int(T*.975)]
def show(rows, lbl, minn=12):
    if len(rows) < minn: print(f"  {lbl:<48} n={len(rows)} too few"); return
    n, h, u, ro = sc(rows); lo, hi = gboot(rows)
    print(f"  {lbl:<48} n={n:<4}{h:>6.1f}%{u:>+8.2f}u{ro:>+8.1f}%  95CI [{lo:+6.1f},{hi:+6.1f}]")

print("="*112)
print("  PART A - THE DRIFT RULE: closing-price version vs the version you can actually act on")
print("="*112)
W = dedupe([r for r in ALL if r["clv"] is not None])
print(f"  whole book, {len(W)} bets with a CLV reading")
show([r for r in W if r["clv"] > 0.01],                    "  CLOSING: price SHORTENED (money agrees)")
show([r for r in W if -0.01 <= r["clv"] <= 0.01],          "  CLOSING: steady")
show([r for r in W if r["clv"] < -0.01],                   "  CLOSING: DRIFTED against us")
show([r for r in W if r["clv"] >= -0.01],                  "  CLOSING: skip-drift ON (what is live)")
print("")
P = dedupe([r for r in ALL if r["pre"] is not None])
print(f"  now the same split using ONLY pre-tip movement, {len(P)} bets with 2+ quotes at one line")
show([r for r in P if r["pre"] < -0.005],                  "  PRE-TIP: price SHORTENED (money agrees)")
show([r for r in P if abs(r["pre"]) <= 0.005],             "  PRE-TIP: steady")
show([r for r in P if r["pre"] > 0.005],                   "  PRE-TIP: DRIFTED against us")
show([r for r in P if r["pre"] <= 0.005],                  "  PRE-TIP: skip-drift ON")
print("")
both = [r for r in ALL if r["clv"] is not None and r["pre"] is not None]
if both:
    agree = sum(1 for r in both if (r["clv"] < -0.01) == (r["pre"] > 0.005))
    print(f"  do the two agree on WHICH bets drifted? {100*agree/len(both):.0f}% of {len(both)}")
    print("  if this is far from 100%, the live gate and the -28% headline are not the same rule.")
print("")
print("="*112)
print("  PART B - CAN OPPONENT SHADE REPLACE GATE 3?  (universe = gates 1+2)")
print("="*112)
U = dedupe([r for r in ALL if r["g1"] and r["g2"] and r["opp"] is not None])
om = statistics.median(r["opp"] for r in U)
print(f"  {len(U)} signal candidates with an opponent-shade reading; split at {om:+.2f}")
print("")
print(f"  {'':<26}{'shade DOWN (keep)':>28}{'shade UP (skip)':>28}")
for lbl, sel in (("gate 3 PASS", lambda r: r["g3"]), ("gate 3 FAIL", lambda r: not r["g3"])):
    a = [r for r in U if sel(r) and r["opp"] <= om]
    b = [r for r in U if sel(r) and r["opp"] > om]
    def cell(x):
        if len(x) < 8: return f"n={len(x)} too few".rjust(28)
        n, h, u, ro = sc(x); return f"n={n:<3} {h:5.1f}%  ROI {ro:+6.1f}%".rjust(28)
    print(f"  {lbl:<26}{cell(a)}{cell(b)}")
print("")
print("  the bottom-left cell is the whole question: if gate-3 FAILURES with a shaded-down")
print("  opponent still win, shade can do gate 3's job and the swap buys back volume.")
print("")
print("="*112)
print("  THE CANDIDATE RULES, SIDE BY SIDE")
print("="*112)
show(U,                                              "  gates 1+2 only, no third gate")
show([r for r in U if r["g3"]],                      "  + gate 3 (MODEL S today)")
show([r for r in U if r["opp"] <= om],               "  + shade INSTEAD of gate 3  (the swap)")
show([r for r in U if r["g3"] and r["opp"] <= om],   "  + both (the stack)")
show([r for r in U if r["g3"] or r["opp"] <= om],    "  + either one passes (widest)")
print("")
tot = len({r["date"] for r in U})
for lbl, g in (("gate 3 (today)", [r for r in U if r["g3"]]),
               ("shade swap", [r for r in U if r["opp"] <= om]),
               ("stack", [r for r in U if r["g3"] and r["opp"] <= om]),
               ("either", [r for r in U if r["g3"] or r["opp"] <= om])):
    print(f"  {lbl:<20} {len(g):>4} bets over {tot} slates = {len(g)/tot:.2f} a night")
