import os, sys, random, statistics, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, D)
from t4_lib import base
R = base()
SIGS = ("flip", "hotover", "overshoot"); BM = ("pra", "pr", "pts")
A = [r for r in R if r["prev"] is not None and r["mk"] in BM]
for r in A: r["mv"] = r["line"]-r["prev"]
gp = [r for r in A if r["mv"] <= 0]
flags = [any(s in SIGS for s in r["srcs"]) for r in gp]
pay = [(r["over"]-1) if r["actual"] > r["line"] else -1.0 for r in gp]
bk = collections.defaultdict(list)
for i, r in enumerate(gp): bk[(r["pl"], r["mk"])].append(i)
sz = collections.Counter(len(v) for v in bk.values())
nsig_blocks = sum(1 for v in bk.values() if any(flags[i] for i in v))
print("gate-PASS rows %d, blocks %d, signal rows %d, blocks containing >=1 signal %d" % (
    len(gp), len(bk), sum(flags), nsig_blocks))
degen = sum(1 for v in bk.values() if len(v) == 1 and any(flags[i] for i in v))
print("  signal rows locked in a size-1 block (permutation cannot move them): %d" % degen)
print("  block size distribution:", sorted(sz.items())[:12])
blocks = list(bk.values())
rr = random.Random(21); sims = []
for _ in range(3000):
    nf = list(flags)
    for idx in blocks:
        v = [flags[i] for i in idx]; rr.shuffle(v)
        for i, x in zip(idx, v): nf[i] = x
    a = [p for p, fl in zip(pay, nf) if fl]; b = [p for p, fl in zip(pay, nf) if not fl]
    sims.append(sum(a)/len(a) - sum(b)/len(b))
real = (sum(p for p, fl in zip(pay, flags) if fl)/sum(flags)
        - sum(p for p, fl in zip(pay, flags) if not fl)/(len(pay)-sum(flags)))
sims.sort()
print("  real diff %+.1f pp | null mean %+.1f pp  sd %.1f pp  p95 %+.1f pp  p = %.4f" % (
    100*real, 100*statistics.mean(sims), 100*statistics.pstdev(sims), 100*sims[int(.95*3000)],
    sum(1 for x in sims if x >= real)/3000))
print("")
# is it player SELECTION? over-ROI of every gate-pass row belonging to a signal-firing player-market
sigblocks = set(k for k, v in bk.items() if any(flags[i] for i in v))
inb = [r for r in gp if (r["pl"], r["mk"]) in sigblocks]
outb = [r for r in gp if (r["pl"], r["mk"]) not in sigblocks]
def roi(v): return 100*sum((r["over"]-1) if r["actual"] > r["line"] else -1.0 for r in v)/len(v)
print("PLAYER-SELECTION CHECK (gate-pass rows only):")
print("  rows in a player-market the signal EVER fires on : n=%-5d ROI %+.1f%%  over-rate %.1f%%" % (
    len(inb), roi(inb), 100*sum(1 for r in inb if r["actual"] > r["line"])/len(inb)))
print("  rows in a player-market it never fires on        : n=%-5d ROI %+.1f%%  over-rate %.1f%%" % (
    len(outb), roi(outb), 100*sum(1 for r in outb if r["actual"] > r["line"])/len(outb)))
sigrows = [r for r in inb if any(s in SIGS for s in r["srcs"])]
nonsig_inb = [r for r in inb if not any(s in SIGS for s in r["srcs"])]
print("  inside those blocks: signal nights n=%-4d ROI %+.1f%% | other nights n=%-4d ROI %+.1f%%" % (
    len(sigrows), roi(sigrows), len(nonsig_inb), roi(nonsig_inb)))
