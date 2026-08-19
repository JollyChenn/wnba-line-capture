# fadehunt.py - two ideas: fade what the gates reject, and read the opponent's board.
# ---------------------------------------------------------------------------------------------
# IDEA 1 - FADE THE REJECTS. gate 2's rejects hit 38.1% as overs and gate 3's hit 40.0%. If those
# overs lose that badly, the unders should win. This is the cheapest volume in the project IF it
# survives one specific trap: the under is NOT priced at 1/over. It has its own quote, and the
# book's margin sits on both sides. A 60% under at 1.55 loses money. So every fade below is priced
# at the ACTUAL Under quote on the same line at the same moment - never inferred.
#
# IDEA 2 - READ THE OPPONENT'S BOARD. gamectx.py died because Pinnacle gamelines only start
# 2026-07-11 and cover 30 of 78 bets. But the game total is knowable another way: the book posts a
# points line for EVERY player in the game. Sum them, or better, compare each to her own median,
# and you get the book's opinion on the pace of that game - with near-total coverage, from data we
# already have. Three features, all knowable before tip:
#   opp_shade   opponent players' lines minus their medians. Book shading the OTHER side up means
#               it expects a fast game, which should help our over.
#   own_shade   her own team-mates' lines minus their medians, excluding her.
#   board_total sum of both teams' points lines - a direct proxy for the game total.
# Noise ceiling is printed BEFORE any of it, at the game level.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260819)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
SIGS = ("flip", "hotover", "overshoot"); BET_MKTS = ("pra", "pr", "pts")

tip_on, gof, oppof = {}, {}, {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    tip_on[(hm, d2)] = t2; tip_on[(aw, d2)] = t2
    gof[(hm, t2)] = gid; gof[(aw, t2)] = gid
    oppof[(hm, t2)] = aw; oppof[(aw, t2)] = hm

def med_before(pl, mk, gt):
    v = [r[mk] for r in hist.get(pl, []) if r["tip"] < gt]
    return statistics.median(v[-10:]) if len(v) >= 3 else None

# ---------- IDEA 1: fade the rejects, at the real Under price -------------------------------
U = []
for r in load("graded_bets.csv"):
    if (r.get("result") or "").upper() not in ("WIN", "LOSS"): continue
    src, mk, pl = (r.get("src") or ""), (r.get("market") or ""), (r.get("player") or "").lower()
    tm = teamof.get(pl)
    gt = tip_on.get((tm, r.get("date") or "")) if tm else None
    if not gt: continue
    now = pgrow.get((pl, gt))
    sd = side.get((pl, mk, gt), {})
    if not now or mk not in now or "Over" not in sd: continue
    ot, oln, ood = sd["Over"]
    if now[mk] == oln: continue
    pv = prevline.get((pl, mk, gt))
    row = dict(pl=pl, mk=mk, gt=gt, gid=gof[(tm, gt)], date=r.get("date"), src=src, tm=tm,
               ln=oln, od=ood, over_won=now[mk] > oln,
               g1=(src in SIGS), g2=(mk in BET_MKTS),
               g3=(pv is not None and oln - pv < 0.5))
    if "Under" in sd and abs(sd["Under"][1] - oln) < 0.01:
        row["u_od"] = sd["Under"][2]; row["u_won"] = now[mk] < oln
    U.append(row)

def dedupe(rows, key="od"):
    best = {}
    for r in sorted(rows, key=lambda x: -(x.get(key) or 0)): best.setdefault((r["pl"], r["gt"]), r)
    return list(best.values())
def scx(rows, wk, ok):
    n = len(rows); w = sum(1 for r in rows if r[wk])
    u = sum((r[ok]-1) if r[wk] else -1.0 for r in rows)
    return n, 100*w/n, u, 100*u/n
def gboot(rows, wk, ok, T=3000):
    bg = collections.defaultdict(list)
    for r in rows: bg[r["gid"]].append(r)
    k = list(bg); o = []
    for _ in range(T):
        g = [x for p in [random.choice(k) for _ in k] for x in bg[p]]
        o.append(100*sum((x[ok]-1) if x[wk] else -1.0 for x in g)/len(g))
    o.sort(); return o[int(T*.025)], o[int(T*.975)]
def show(rows, lbl, wk, ok, minn=12):
    rows = [r for r in rows if ok in r]
    if len(rows) < minn: print(f"  {lbl:<50} n={len(rows)} too few"); return
    n, h, u, ro = scx(rows, wk, ok); lo, hi = gboot(rows, wk, ok)
    print(f"  {lbl:<50} n={n:<4}{h:>6.1f}%{u:>+8.2f}u{ro:>+8.1f}%  95CI [{lo:+6.1f},{hi:+6.1f}]")

haveU = [r for r in U if "u_od" in r]
print(f"{len(U)} settled bets with an Over quote; {len(haveU)} also have a matching Under quote")
if haveU:
    mo = statistics.mean(r["od"] for r in haveU); mu = statistics.mean(r["u_od"] for r in haveU)
    print(f"  mean Over {mo:.3f}  mean Under {mu:.3f}  ->  book margin "
          f"{100*(1/mo + 1/mu - 1):.1f}%   (this is what a fade has to beat)")
print("")
print("="*112)
print("  IDEA 1: FADE THE REJECTS - bet the UNDER on what the gates throw out")
print("="*112)
g2rej = dedupe([r for r in haveU if r["g1"] and not r["g2"]], "u_od")
g3rej = dedupe([r for r in haveU if r["g1"] and r["g2"] and not r["g3"]], "u_od")
g1rej = dedupe([r for r in haveU if not r["g1"]], "u_od")
mS    = dedupe([r for r in haveU if r["g1"] and r["g2"] and r["g3"]], "u_od")
for rows, lbl in ((g2rej, "gate 2 rejects"), (g3rej, "gate 3 rejects"),
                  (g1rej, "gate 1 rejects"), (mS, "MODEL S itself (control)")):
    show(rows, f"  {lbl}: the OVER", "over_won", "od")
    show(rows, f"  {lbl}: the FADE (under)", "u_won", "u_od")
    print("")
print("  a fade only works if the under's own price leaves room after the book's margin.")
print("")

# ---------- IDEA 2: the opponent's board ----------------------------------------------------
# every player's last pts line per game, and how far it sits from her own median
shade = collections.defaultdict(list)   # (team, gt) -> [line - median, ...]
ptsline = collections.defaultdict(list)  # (team, gt) -> [line, ...]
for (pl, mk, gt), sdq in side.items():
    if mk != "pts" or "Over" not in sdq: continue
    tm = teamof.get(pl)
    if not tm: continue
    ln = sdq["Over"][1]
    ptsline[(tm, gt)].append(ln)
    m = med_before(pl, "pts", gt)
    if m is not None: shade[(tm, gt)].append(ln - m)

S = dedupe([r for r in U if r["g1"] and r["g2"] and r["g3"]], "od")
for r in S:
    op = oppof.get((r["tm"], r["gt"]))
    o_s = shade.get((op, r["gt"]), []); w_s = [x for x in shade.get((r["tm"], r["gt"]), [])]
    r["opp_shade"] = statistics.mean(o_s) if len(o_s) >= 3 else None
    r["own_shade"] = statistics.mean(w_s) if len(w_s) >= 3 else None
    a, b = ptsline.get((r["tm"], r["gt"]), []), ptsline.get((op, r["gt"]), [])
    r["btot"] = (sum(a) + sum(b)) if (len(a) >= 4 and len(b) >= 4) else None
cov = sum(1 for r in S if r["opp_shade"] is not None)
print("="*112)
print(f"  IDEA 2: THE OPPONENT'S BOARD - coverage {cov} of {len(S)} Model S bets"
      f"   (Pinnacle managed 30)")
print("="*112)

bg = collections.defaultdict(list)
for r in S: bg[r["gid"]].append(r)
gk = list(bg)
peaks = []
for _ in range(3000):
    bc = -99
    for _ in range(9):
        cut = random.random(); lab = {g: random.random() for g in gk}
        pick = [x for g in gk if lab[g] < cut for x in bg[g]]
        if len(pick) >= 15: bc = max(bc, scx(pick, "over_won", "od")[3])
    if bc > -99: peaks.append(bc)
peaks.sort()
print(f"  noise ceiling first: 9 random game-level splits reach {peaks[int(len(peaks)*0.95)]:+.1f}% at p95.")
print("")
for feat, lbl in (("opp_shade", "OPPONENT lines vs their medians"),
                  ("own_shade", "HER OWN TEAM's lines vs medians"),
                  ("btot", "board-implied game total")):
    v = sorted(r[feat] for r in S if r.get(feat) is not None)
    if len(v) < 30: print(f"  {lbl}: n={len(v)} too few"); print(""); continue
    lo3, hi3 = v[len(v)//3], v[2*len(v)//3]
    print(f"  {lbl}   (terciles at {lo3:+.2f} / {hi3:+.2f})" if feat != "btot"
          else f"  {lbl}   (terciles at {lo3:.1f} / {hi3:.1f})")
    show([r for r in S if r.get(feat) is not None and r[feat] <= lo3], "    LOW  third", "over_won", "od")
    show([r for r in S if r.get(feat) is not None and lo3 < r[feat] <= hi3], "    MID  third", "over_won", "od")
    show([r for r in S if r.get(feat) is not None and r[feat] > hi3], "    HIGH third", "over_won", "od")
    print("")
