# C1 part two: the gate as a board-wide gradient (large n, low noise) and the decomposition
# of Model S into "gate" and "signal" contributions.
import platform; platform._wmi = None
import os, sys, json, math, random, statistics, collections
import numpy as np
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, D)
from t4_lib import base, boot_ci_by_game
R = base()
SIGS = ("flip", "hotover", "overshoot"); BM = ("pra", "pr", "pts")
LOG = []
def P(s=""):
    print(s); LOG.append(s)

A = [r for r in R if r["prev"] is not None and r["sd"]]
for r in A: r["mv"] = r["line"] - r["prev"]
P("="*100)
P("C1b  THE GATE AS A BOARD-WIDE GRADIENT  (n=%d quotes, %d games, %d players)" % (
    len(A), len(set(r["gt"] for r in A)), len(set(r["pl"] for r in A))))
P("="*100)
P("  Law 6 mechanism check, on RAW PRODUCTION not on ROI:")
P("     Spearman-ish: mean standardised beat (actual-line)/sd by line move")
for mv in sorted(set(round(r["mv"]) for r in A)):
    v = [r for r in A if round(r["mv"]) == mv]
    if len(v) < 30: continue
    z = statistics.mean((r["actual"]-r["line"])/r["sd"] for r in v)
    w = sum(1 for r in v if r["actual"] > r["line"])/len(v)
    P("        mv %+d  n=%-5d over-rate %.1f%%  mean z %+.3f" % (mv, len(v), 100*w, z))
# rank correlation between mv and standardised beat, permuted at PLAYER block
xs = np.array([r["mv"] for r in A]); ys = np.array([(r["actual"]-r["line"])/r["sd"] for r in A])
def spear(x, y):
    rx = np.argsort(np.argsort(x)).astype(float); ry = np.argsort(np.argsort(y)).astype(float)
    rx -= rx.mean(); ry -= ry.mean()
    return float((rx@ry)/math.sqrt((rx@rx)*(ry@ry)))
rho = spear(xs, ys)
rr = random.Random(3)
byp = collections.defaultdict(list)
for i, r in enumerate(A): byp[r["pl"]].append(i)
plists = [np.array(v) for v in byp.values()]
rng = np.random.default_rng(1)
T = 3000; beat = 0
for _ in range(T):
    yy = ys.copy()
    for idx in plists: yy[idx] = rng.permutation(yy[idx])
    if spear(xs, yy) <= rho: beat += 1
p_rho = (beat+1)/(T+1)
P("     rho(line move, standardised beat) = %+.4f   player-block permutation p (one-sided, negative) = %.4f"
  % (rho, p_rho))
byg = collections.defaultdict(list)
for i, r in enumerate(A): byg[r["gt"]].append(i)
glists = [np.array(v) for v in byg.values()]
beat = 0
for _ in range(T):
    yy = ys.copy()
    for idx in glists: yy[idx] = rng.permutation(yy[idx])
    if spear(xs, yy) <= rho: beat += 1
P("     same, permuted inside GAME blocks: p = %.4f" % ((beat+1)/(T+1)))
P("")
P("  BUT the gate alone does not clear the price. Over-side ROI by line move on the whole board:")
for lab, sel in (("cut (mv<=-1)", lambda r: r["mv"] <= -1), ("flat (mv==0)", lambda r: r["mv"] == 0),
                 ("raised (mv>=1)", lambda r: r["mv"] >= 1), ("gate PASS (mv<=0)", lambda r: r["mv"] <= 0)):
    v = [r for r in A if sel(r)]
    roi = sum((r["over"]-1) if r["actual"] > r["line"] else -1.0 for r in v)/len(v)
    lo, hi = boot_ci_by_game([(r["gt"], r["over"], r["actual"] > r["line"]) for r in v], 3000, 4)
    P("     %-17s n=%-5d ROI %+6.1f%%  CI[%+.1f%%, %+.1f%%]" % (lab, len(v), 100*roi, 100*lo, 100*hi))
P("")
P("  DECOMPOSITION of Model S -- 2x2, gate x signal, on the same board, same instant:")
P("     %-24s %8s %8s %8s" % ("", "n", "over%", "ROI"))
for lab, sel in (("no signal, gate FAIL", lambda r: not any(s in SIGS for s in r["srcs"]) and r["mv"] >= 1),
                 ("no signal, gate PASS", lambda r: not any(s in SIGS for s in r["srcs"]) and r["mv"] <= 0),
                 ("signal,    gate FAIL", lambda r: any(s in SIGS for s in r["srcs"]) and r["mv"] >= 1),
                 ("signal,    gate PASS", lambda r: any(s in SIGS for s in r["srcs"]) and r["mv"] <= 0)):
    v = [r for r in A if sel(r) and r["mk"] in BM]
    if not v: continue
    roi = sum((r["over"]-1) if r["actual"] > r["line"] else -1.0 for r in v)/len(v)
    w = sum(1 for r in v if r["actual"] > r["line"])/len(v)
    P("     %-24s %8d %7.1f%% %+7.1f%%" % (lab, len(v), 100*w, 100*roi))
P("     -> gate main effect (no-signal rows, %d quotes): %+.1f pp of ROI" % (
    len([r for r in A if not any(s in SIGS for s in r["srcs"]) and r["mk"] in BM]),
    100*(sum((r["over"]-1) if r["actual"]>r["line"] else -1.0 for r in A if not any(s in SIGS for s in r["srcs"]) and r["mk"] in BM and r["mv"]<=0)/max(1,len([r for r in A if not any(s in SIGS for s in r["srcs"]) and r["mk"] in BM and r["mv"]<=0]))
       - sum((r["over"]-1) if r["actual"]>r["line"] else -1.0 for r in A if not any(s in SIGS for s in r["srcs"]) and r["mk"] in BM and r["mv"]>=1)/max(1,len([r for r in A if not any(s in SIGS for s in r["srcs"]) and r["mk"] in BM and r["mv"]>=1])))))
P("")
P("  IS THE SIGNAL ITSELF WORTH ANYTHING? restrict to gate-PASS rows and compare signal vs not.")
gp = [r for r in A if r["mv"] <= 0 and r["mk"] in BM]
sg = [r for r in gp if any(s in SIGS for s in r["srcs"])]
ng = [r for r in gp if not any(s in SIGS for s in r["srcs"])]
def roi_(v): return sum((r["over"]-1) if r["actual"] > r["line"] else -1.0 for r in v)/len(v)
P("     signal    n=%-5d ROI %+.1f%%" % (len(sg), 100*roi_(sg)))
P("     no signal n=%-5d ROI %+.1f%%" % (len(ng), 100*roi_(ng)))
# permutation: reassign the signal flag across player-market blocks inside the gate-pass set
flags = [any(s in SIGS for s in r["srcs"]) for r in gp]
real = roi_(sg) - roi_(ng)
bk = collections.defaultdict(list)
for i, r in enumerate(gp): bk[(r["pl"], r["mk"])].append(i)
blocks = list(bk.values())
rr2 = random.Random(21); beat = 0; T2 = 3000
pay = [(r["over"]-1) if r["actual"] > r["line"] else -1.0 for r in gp]
for _ in range(T2):
    nf = list(flags)
    for idx in blocks:
        v = [flags[i] for i in idx]; rr2.shuffle(v)
        for i, x in zip(idx, v): nf[i] = x
    a = [p for p, fl in zip(pay, nf) if fl]; b = [p for p, fl in zip(pay, nf) if not fl]
    if a and b and (sum(a)/len(a) - sum(b)/len(b)) >= real: beat += 1
P("     signal-minus-nosignal inside gate-PASS = %+.1f pp   perm p (player-market block) = %.4f"
  % (100*real, (beat+1)/(T2+1)))
P("")
P("  A ONE-SAMPLE TEST ON MODEL S ITSELF (game-clustered bootstrap, is ROI > 0?):")
ms = [r for r in A if any(s in SIGS for s in r["srcs"]) and r["mk"] in BM and r["mv"] <= 0]
best = {}
for r in ms:
    k = (r["pl"], r["date"])
    if k not in best or (r["mk"], r["gt"]) < (best[k]["mk"], best[k]["gt"]): best[k] = r
ms = list(best.values())
bts = [(r["gt"], r["over"], r["actual"] > r["line"]) for r in ms]
byg2 = collections.defaultdict(list)
for g, p, w in bts: byg2[g].append((p, w))
keys = list(byg2); rr3 = random.Random(9); out = []
for _ in range(6000):
    t = 0.0; n = 0
    for _ in range(len(keys)):
        for p, w in byg2[keys[rr3.randrange(len(keys))]]:
            t += (p-1) if w else -1.0; n += 1
    out.append(t/n)
out.sort()
pz = sum(1 for x in out if x <= 0)/len(out)
P("     Model S n=%d games=%d ROI %+.1f%%  bootstrap P(ROI<=0) = %.4f  (this is the honest one-sided p)"
  % (len(ms), len(keys), 100*statistics.mean((r["over"]-1) if r["actual"] > r["line"] else -1.0 for r in ms), pz))
json.dump({"p_rho_player": p_rho, "p_ms_boot": pz}, open(os.path.join(D, "outputs", "t4_c1b.json"), "w"))
open(os.path.join(D, "outputs", "t4_c1b.txt"), "w", encoding="utf-8").write("\n".join(LOG))
