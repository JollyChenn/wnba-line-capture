# The decisive within-player test for C1: among gate-PASS quotes belonging to player-markets
# the signal DOES fire on, does it fire on the right NIGHTS? Null = shuffle the signal flag
# inside each player-market block, so between-player quality cancels exactly.
import platform; platform._wmi = None
import os, sys, json, random, statistics, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, D)
from t4_lib import base, boot_ci_by_game
R = base()
SIGS = ("flip", "hotover", "overshoot"); BM = ("pra", "pr", "pts")
LOG = []
def P(s=""):
    print(s); LOG.append(s)
A = [r for r in R if r["prev"] is not None and r["mk"] in BM]
for r in A: r["mv"] = r["line"]-r["prev"]
def roi(v): return (sum((r["over"]-1) if r["actual"] > r["line"] else -1.0 for r in v)/len(v)) if v else 0.0
def sig(r): return any(s in SIGS for s in r["srcs"])

P("="*100)
P("C1d  WITHIN-PLAYER TIMING TEST  (between-player quality differenced out by construction)")
P("="*100)
for gname, gsel in (("gate PASS (mv<=0)", lambda r: r["mv"] <= 0),
                    ("gate FAIL (mv>=1)", lambda r: r["mv"] >= 1),
                    ("all rows", lambda r: True)):
    S = [r for r in A if gsel(r)]
    byb = collections.defaultdict(list)
    for r in S: byb[(r["pl"], r["mk"])].append(r)
    byb = {k: v for k, v in byb.items() if any(sig(r) for r in v) and len(v) >= 2}
    rows = [r for v in byb.values() for r in v]
    a = [r for r in rows if sig(r)]; b = [r for r in rows if not sig(r)]
    if not a or not b: continue
    real = roi(a) - roi(b)
    blocks = [[i for i, r in enumerate(rows) if (r["pl"], r["mk"]) == k] for k in byb]
    flags = [sig(r) for r in rows]
    pay = [(r["over"]-1) if r["actual"] > r["line"] else -1.0 for r in rows]
    rr = random.Random(41); sims = []
    for _ in range(4000):
        nf = list(flags)
        for idx in blocks:
            v = [flags[i] for i in idx]; rr.shuffle(v)
            for i, x in zip(idx, v): nf[i] = x
        aa = [p for p, fl in zip(pay, nf) if fl]; bb = [p for p, fl in zip(pay, nf) if not fl]
        if aa and bb: sims.append(sum(aa)/len(aa) - sum(bb)/len(bb))
    sims.sort()
    pv = sum(1 for x in sims if x >= real)/len(sims)
    P("  %-18s blocks=%-4d  signal n=%-4d ROI %+6.1f%%  |  same players, quiet n=%-5d ROI %+6.1f%%"
      % (gname, len(byb), len(a), 100*roi(a), len(b), 100*roi(b)))
    P("  %-18s within-block diff %+6.1f pp | null mean %+.1f pp sd %.1f pp -> p = %.4f"
      % ("", 100*real, 100*statistics.mean(sims), 100*statistics.pstdev(sims), pv))
    if gname.startswith("gate PASS"):
        json.dump({"p_timing_gatepass": pv, "diff": real, "n_sig": len(a)},
                  open(os.path.join(D, "outputs", "t4_c1d.json"), "w"))
P("")
P("  SAME TEST, but on RAW PRODUCTION rather than ROI (Law 6). Statistic = mean of")
P("  (actual - line)/player_sd, so the book's price cannot create the result.")
S = [r for r in A if r["mv"] <= 0 and r["sd"]]
byb = collections.defaultdict(list)
for r in S: byb[(r["pl"], r["mk"])].append(r)
byb = {k: v for k, v in byb.items() if any(sig(r) for r in v) and len(v) >= 2}
rows = [r for v in byb.values() for r in v]
z = [(r["actual"]-r["line"])/r["sd"] for r in rows]
flags = [sig(r) for r in rows]
blocks = [[i for i, r in enumerate(rows) if (r["pl"], r["mk"]) == k] for k in byb]
real = (statistics.mean([x for x, fl in zip(z, flags) if fl])
        - statistics.mean([x for x, fl in zip(z, flags) if not fl]))
rr = random.Random(43); sims = []
for _ in range(4000):
    nf = list(flags)
    for idx in blocks:
        v = [flags[i] for i in idx]; rr.shuffle(v)
        for i, x in zip(idx, v): nf[i] = x
    aa = [x for x, fl in zip(z, nf) if fl]; bb = [x for x, fl in zip(z, nf) if not fl]
    sims.append(sum(aa)/len(aa) - sum(bb)/len(bb))
sims.sort()
pz = sum(1 for x in sims if x >= real)/len(sims)
P("     signal nights mean z %+.3f  |  her other gate-pass nights %+.3f  |  diff %+.3f  p = %.4f" % (
    statistics.mean([x for x, fl in zip(z, flags) if fl]),
    statistics.mean([x for x, fl in zip(z, flags) if not fl]), real, pz))
P("")
P("  WALK-FORWARD on the within-player timing effect (3 chronological game folds):")
gs = sorted(set(r["gt"] for r in rows)); sz = len(gs)/3
for i in range(3):
    sel = set(gs[int(i*sz):int((i+1)*sz)])
    a = [r for r in rows if r["gt"] in sel and sig(r)]
    b = [r for r in rows if r["gt"] in sel and not sig(r)]
    if not a: continue
    P("     fold %d  %s..%s  signal n=%-3d ROI %+6.1f%%  quiet n=%-4d ROI %+6.1f%%  diff %+6.1f pp" % (
        i+1, min(r["date"] for r in a), max(r["date"] for r in a),
        len(a), 100*roi(a), len(b), 100*roi(b), 100*(roi(a)-roi(b))))
json.dump({"p_timing_raw": pz}, open(os.path.join(D, "outputs", "t4_c1d_raw.json"), "w"))
open(os.path.join(D, "outputs", "t4_c1d.txt"), "w", encoding="utf-8").write("\n".join(LOG))
