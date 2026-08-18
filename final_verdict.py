# final_verdict.py - Model S, fully defined, on every bet the engine ACTUALLY PINGED.
# ---------------------------------------------------------------------------------------------
# Every number quoted so far has been one of two unsatisfying things:
#   * a BACKTEST over the whole board, where the engine's signal was reconstructed rather than
#     recorded, and which failed the within-player null
#   * model_forward.csv, which is n=13 - too small to say anything about anything
#
# There is a third source nobody has used properly. graded_bets.csv holds 869 bets the engine
# EMITTED LIVE and that were settled afterwards. The signal selection in it is genuinely forward -
# it was chosen before the game, by the live code, with no knowledge of the result. What is
# missing is gate 3, the star, because that gate was added to the card later and graded_bets does
# not carry a previous-line column.
#
# So: reconstruct gate 3 from the board archive and apply the FULL Model S definition to bets that
# were really pinged. That is the largest honest estimate available - forward on signal selection,
# retrospective only on the star. It is the number that answers "is the model good".
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260921)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
SIGS = ("flip", "hotover", "overshoot"); BET_MKTS = ("pra", "pr", "pts")

# date -> the tip of that player's game, so a graded row can find its previous line
tip_on = {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    tip_on[(hm, d2)] = t2; tip_on[(aw, d2)] = t2

G = []
miss = collections.Counter()
for r in load("graded_bets.csv"):
    res = (r.get("result") or "").upper()
    if res not in ("WIN", "LOSS"): continue
    src, mk = (r.get("src") or ""), (r.get("market") or "")
    pl = (r.get("player") or "").lower()
    od, dt = f(r.get("odds")), (r.get("date") or "")
    if od is None: miss["no odds"] += 1; continue
    tm = teamof.get(pl)
    if not tm: miss["player not in box"] += 1; continue
    gt = tip_on.get((tm, dt))
    if not gt: miss["no game that date"] += 1; continue
    ln = f(r.get("line"))
    pv = prevline.get((pl, mk, gt))
    G.append(dict(pl=pl, name=r.get("player"), mk=mk, src=src, date=dt, gt=gt, line=ln, od=od,
                  won=(res == "WIN"), prev=pv,
                  raised=(pv is None or (ln is not None and ln - pv >= 0.5)),
                  noprev=(pv is None),
                  clv=f(r.get("odds_clv")), sclv=f(r.get("sharp_clv"))))
print(f"{len(G)} live-pinged settled bets matched to a game   (unmatched: {dict(miss)})")
print("")

def dedupe(rows):
    best = {}
    for r in sorted(rows, key=lambda x: -x["od"]): best.setdefault((r["pl"], r["gt"]), r)
    return sorted(best.values(), key=lambda r: r["date"])
def roi(rows): return 100*sum((r["od"]-1) if r["won"] else -1.0 for r in rows)/len(rows) if rows else 0.0
def pboot(rows, T=4000):
    bp = collections.defaultdict(list)
    for r in rows: bp[r["pl"]].append(r)
    keys = list(bp)
    if len(keys) < 8: return None, None
    o = []
    for _ in range(T):
        pick = [random.choice(keys) for _ in keys]
        o.append(roi([x for k in pick for x in bp[k]]))
    o.sort(); return o[int(T*.025)], o[int(T*.975)]
def show(rows, label, minn=20):
    n = len(rows)
    if n < minn: print(f"  {label:<40} n={n:<4} too few"); return
    w = sum(1 for r in rows if r["won"]); u = sum((r["od"]-1) if r["won"] else -1.0 for r in rows)
    lo, hi = pboot(rows)
    cl = [r["clv"] for r in rows if r["clv"] is not None]
    ci = f"[{lo:+6.1f},{hi:+6.1f}]" if lo is not None else "      -       "
    print(f"  {label:<40} n={n:<4} {100*w/n:5.1f}%  {u:+7.2f}u  ROI {100*u/n:+6.1f}%  95CI {ci}"
          + (f"  clv {statistics.mean(cl):+.3f}" if cl else ""))

print("="*104)
print("  BUILDING MODEL S ONE GATE AT A TIME")
print("="*104)
g1 = [r for r in G if r["src"] in SIGS]
g2 = [r for r in g1 if r["mk"] in BET_MKTS]
g3 = [r for r in g2 if not r["raised"]]
g4 = dedupe(g3)
show(G,  "  everything the engine pinged")
show(g1, "  + gate 1: src in the 3 signals")
show(g2, "  + gate 2: market in pra/pr/pts")
show(g3, "  + gate 3: book did not raise her")
show(g4, "  + gate 4: one position per player  = MODEL S")
print("")
print("="*104)
print("  WHAT EACH GATE THREW AWAY - a gate that helps must leave a WORSE residue behind")
print("="*104)
show([r for r in G  if r["src"] not in SIGS],             "  cut by gate 1 (other srcs)")
show([r for r in g1 if r["mk"] not in BET_MKTS],          "  cut by gate 2 (pa/ra/reb/ast)")
show([r for r in g2 if r["raised"] and not r["noprev"]],  "  cut by gate 3: RAISED")
show([r for r in g2 if r["noprev"]],                      "  cut by gate 3: NO PREVIOUS LINE")
print("")
print("="*104)
print("  MODEL S BY SIGNAL")
print("="*104)
for s in SIGS: show([r for r in g4 if r["src"] == s], f"  {s}")
print("")
print("="*104)
print("  OUT OF SAMPLE")
print("="*104)
dts = sorted({r["date"] for r in g4}); cut = dts[int(len(dts)*0.6)]
print(f"  split {cut}")
show([r for r in g4 if r["date"] <  cut], "    MODEL S  IN ")
show([r for r in g4 if r["date"] >= cut], "    MODEL S  OUT")
print("")
print("="*104)
print("  IS THE STAR DOING ANYTHING? permutation on the star label, within player")
print("="*104)
bp = collections.defaultdict(list)
for r in dedupe(g2): bp[r["pl"]].append(r)
want = collections.Counter(r["pl"] for r in g4)
real = roi(g4)
T = 5000; beat = 0; sims = []
for _ in range(T):
    out = []
    for p, c in want.items():
        pool = bp.get(p, [])
        out.extend(random.sample(pool, c) if len(pool) > c else pool)
    v = roi(out); sims.append(v)
    if v >= real: beat += 1
sims.sort()
print(f"  MODEL S (star-chosen bets): {real:+.1f}%")
print(f"  same players, same counts, RANDOM bets from gate-2 pool: median {sims[T//2]:+.1f}%  "
      f"p95 {sims[int(T*.95)]:+.1f}%")
print(f"  WITHIN-PLAYER p = {beat/T:.4f}")
print("")
print("="*104)
print("  CLV - the proof standard")
print("="*104)
for lbl, rows in (("MODEL S", g4), ("gate-2 pool", dedupe(g2)), ("everything pinged", G)):
    cl = [r["clv"] for r in rows if r["clv"] is not None]
    sc = [r["sclv"] for r in rows if r["sclv"] is not None]
    if not cl: continue
    m = statistics.mean(cl); se = (statistics.pstdev(cl)/math.sqrt(len(cl))) if len(cl) > 1 else 0
    print(f"  {lbl:<20} odds_clv {m:+.4f} +/- {1.96*se:.4f} (n={len(cl)})"
          + (f"   sharp_clv {statistics.mean(sc):+.3f} (n={len(sc)})" if sc else ""))
print("")
print("  positive odds_clv = we are consistently taking a better price than the market closes at.")
print("  that is the one thing that cannot be produced by luck over a few hundred bets.")
