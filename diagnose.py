# diagnose.py - is the live losing run variance, or is the model degrading?
# ---------------------------------------------------------------------------------------------
# Live: 13 Model S bets, 6-7, -1.77u, -13.6%. Backtest said 64% and +18.7%. From inside a losing
# run these two explanations look identical, so guessing is worthless. They can be separated:
#
#   IF IT IS VARIANCE   the live bets should look exactly like the backtest bets in every way we
#                       can measure before the result - same cushions, same prices, same signal
#                       mix, same star margins. Only the outcomes differ.
#   IF IT IS DEGRADING  something about the bets themselves has changed. The book got sharper, the
#                       lines we are being offered are thinner, the median is staler in August than
#                       it was in June. That shows up in the INPUTS, not just the results.
#
# So compare the 13 live bets against the backtest population feature by feature, then ask how
# unusual -1.77u actually is for a true +18.7% model over 13 bets.
#
# All medians here are CURRENT-TEAM filtered, the way overshoot_overs does it. The unfiltered
# version I used earlier today put an All-Star game into Allisha Gray's median and moved her
# across the cushion-3 line, so every cushion figure below is rebuilt.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260820)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
SIGS = ("flip", "hotover", "overshoot"); BET_MKTS = ("pra", "pr", "pts")

tip_on, gof = {}, {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    tip_on[(hm, d2)] = t2; tip_on[(aw, d2)] = t2
    gof[(hm, t2)] = gid; gof[(aw, t2)] = gid

def med_team(pl, mk, gt):
    g = [r for r in hist.get(pl, []) if r["tip"] < gt]
    if not g: return None
    cur = g[-1]["tm"]; g = [r for r in g if r["tm"] == cur]
    if len(g) < 5: return None
    return statistics.median([r[mk] for r in g[-10:]])

def build(pl, mk, gt, src, date, line=None, odds=None, won=None):
    now = pgrow.get((pl, gt)); sdq = side.get((pl, mk, gt), {})
    if not now or mk not in now: return None
    if line is None:
        if "Over" not in sdq: return None
        line, odds = sdq["Over"][1], sdq["Over"][2]
        won = now[mk] > line
    pv = prevline.get((pl, mk, gt))
    md = med_team(pl, mk, gt)
    return dict(pl=pl, mk=mk, gt=gt, gid=gof.get((teamof.get(pl), gt)), date=date, src=src,
                line=line, od=odds, won=won, med=md,
                cush=(md - line) if md is not None else None,
                prev=pv, starmargin=((pv - line) if pv is not None else None))

# ---- the backtest population (graded_bets, Model S construction) ---------------------------
BT = []
for r in load("graded_bets.csv"):
    if (r.get("result") or "").upper() not in ("WIN", "LOSS"): continue
    src, mk, pl = (r.get("src") or ""), (r.get("market") or ""), (r.get("player") or "").lower()
    if src not in SIGS or mk not in BET_MKTS: continue
    tm = teamof.get(pl)
    gt = tip_on.get((tm, r.get("date") or "")) if tm else None
    if not gt: continue
    now = pgrow.get((pl, gt)); sdq = side.get((pl, mk, gt), {})
    if not now or "Over" not in sdq: continue
    ln = sdq["Over"][1]; pv = prevline.get((pl, mk, gt))
    if pv is None or ln - pv >= 0.5 or now[mk] == ln: continue
    b = build(pl, mk, gt, src, r.get("date"))
    if b: BT.append(b)
seen = {}
for b in sorted(BT, key=lambda x: -x["od"]): seen.setdefault((b["pl"], b["gt"]), b)
BT = sorted(seen.values(), key=lambda x: x["date"])

# ---- the live card population (model_forward) -----------------------------------------------
LV = []
for r in csv.DictReader(open(os.path.join(D, "model_forward.csv"), encoding="utf-8")):
    if (r.get("result") or "").upper() not in ("WIN", "LOSS"): continue
    src, mk, pl = (r.get("src") or ""), (r.get("market") or ""), (r.get("player") or "").lower()
    if src not in SIGS or mk not in BET_MKTS: continue
    tm = teamof.get(pl)
    if not tm: continue
    # keep this offset-AWARE: gmeta's tips come from ts(), which parses the trailing Z into a
    # +00:00 offset, and a naive/aware subtraction raises rather than silently misaligning.
    try: gt = datetime.datetime.fromisoformat(r["tip"].replace("Z", "+00:00"))
    except Exception: continue
    cand = [t for t in {v for k, v in tip_on.items() if k[0] == tm}
            if abs((t - gt).total_seconds()) < 7200]
    if not cand: continue
    b = build(pl, mk, cand[0], src, r.get("slate"), float(r["line"]), float(r["odds"]),
              r["result"].upper() == "WIN")
    if b: LV.append(b)
print(f"backtest population {len(BT)} bets   |   live card {len(LV)} bets")
print("")

def d(rows, k):
    v = [r[k] for r in rows if r.get(k) is not None]
    return (statistics.mean(v), statistics.median(v), len(v)) if v else (None, None, 0)
print("="*96)
print("  1. DO THE LIVE BETS LOOK DIFFERENT FROM THE BACKTEST BETS?")
print("="*96)
print(f"  {'feature':<26}{'backtest':>22}{'live':>22}")
for k, lbl in (("cush", "cushion below median"), ("od", "decimal odds"),
               ("line", "line size"), ("starmargin", "star margin (prev - now)")):
    a = d(BT, k); b = d(LV, k)
    if a[0] is None or b[0] is None: continue
    print(f"  {lbl:<26}{('mean %.2f  med %.1f' % (a[0], a[1])):>22}"
          f"{('mean %.2f  med %.1f' % (b[0], b[1])):>22}")
print("")
for pop, lbl in ((BT, "backtest"), (LV, "live")):
    c = collections.Counter(r["src"] for r in pop); n = len(pop)
    print(f"  {lbl:<10} signal mix: " + ", ".join(f"{k} {100*v/n:.0f}%" for k, v in c.most_common()))
    c2 = collections.Counter(r["mk"] for r in pop)
    print(f"  {'':<10} market mix: " + ", ".join(f"{k} {100*v/n:.0f}%" for k, v in c2.most_common()))
print("")
deep = lambda pop: 100*sum(1 for r in pop if r.get("cush") is not None and r["cush"] >= 3)/max(
    sum(1 for r in pop if r.get("cush") is not None), 1)
print(f"  share with cushion 3+ :  backtest {deep(BT):.0f}%   live {deep(LV):.0f}%")
print("")
print("="*96)
print("  2. HAS THE BACKTEST ITSELF BEEN FADING OVER TIME?")
print("="*96)
dts = sorted({r["date"] for r in BT})
for i in range(3):
    lo = dts[int(len(dts)*i/3)]; hi = dts[min(int(len(dts)*(i+1)/3), len(dts)-1)]
    g = [r for r in BT if lo <= r["date"] <= hi]
    if len(g) < 10: continue
    n = len(g); w = sum(1 for r in g if r["won"])
    u = sum((r["od"]-1) if r["won"] else -1.0 for r in g)
    print(f"    {lo} .. {hi}   n={n:<4}{100*w/n:>6.1f}%   ROI {100*u/n:+6.1f}%")
print("")
print("  if the last third is much worse than the first, the book has been catching up and this")
print("  is not variance. if all three are similar, the live run is just a bad patch.")
print("")
print("="*96)
print("  3. HOW UNUSUAL IS -1.77u OVER 13 BETS, IF THE MODEL IS REAL?")
print("="*96)
odds = [r["od"] for r in LV] or [1.85]*13
real = sum((r["od"]-1) if r["won"] else -1.0 for r in LV)
for p, lbl in ((0.641, "a true 64.1% model (the backtest)"),
               (0.560, "a true 56% model (half the edge)"),
               (1/statistics.mean(odds), "a coin at these prices (no edge)")):
    sims = []
    for _ in range(20000):
        sims.append(sum((o-1) if random.random() < p else -1.0 for o in odds))
    sims.sort()
    worse = sum(1 for s in sims if s <= real)/len(sims)
    print(f"  {lbl:<38} P(P&L <= {real:+.2f}u after {len(odds)} bets) = {100*worse:4.1f}%"
          f"   median {statistics.median(sims):+.2f}u")
print("")
print("  a result that a real model produces 20-30% of the time is not evidence of anything.")
print("  a result it produces 2% of the time is.")
