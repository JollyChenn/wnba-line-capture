# newfilter.py - hunt for a new gate INSIDE Model S, with the nulls built in from the start.
# ------------------------------------------------------------------------------------------
# Power warning up front: this universe is 129 bets (gates 1+2) of which 75 are starred. Cutting
# that many ways will throw up +40% cells that mean nothing. So the ceiling is computed FIRST and
# printed with the findings, and nothing below it gets reported as a finding.
# Every feature is knowable at ping time - no outcome, no closing line, no hindsight.
import csv, os, sys, random, collections, statistics, math
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260927)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "gate5.py"), encoding="utf-8").read()
     .split('print(f"{len(A)} bets with gates 1+2 on')[0])

# enrich each bet with everything the card knows at ping time
for r in A:
    pl, mk, gt = r["pl"], r["mk"], r["gt"]
    q = seq.get((pl, mk, gt), [])
    prior = [x for x in hist.get(pl, []) if x["tip"] < gt]
    p10 = prior[-10:]
    r["med"] = statistics.median(x[mk] for x in p10) if len(p10) >= 6 else None
    r["cush"] = (r["med"] - r["ln"]) if r["med"] is not None else None   # how far below her median
    r["nq"] = len(q)
    r["hrs"] = (gt - q[-1][0]).total_seconds()/3600 if q else None
    r["sd"] = statistics.pstdev([x[mk] for x in p10]) if len(p10) >= 6 else None
    r["cushsd"] = (r["cush"]/r["sd"]) if (r["cush"] is not None and r["sd"]) else None
    pv = prevline.get((pl, mk, gt))
    r["pvmove"] = (r["ln"] - pv) if pv is not None else None
    r["rest"] = (gt - prior[-1]["tip"]).total_seconds()/86400 if prior else None
    r["mins"] = statistics.mean(x["min"] for x in prior[-3:]) if len(prior) >= 3 else None
S = [r for r in A if r["star"] == "starred"]
print(f"universe: {len(A)} bets after gates 1+2 | {len(S)} after gate 3 (Model S)")
def roiof(rows): return 100*sum((r["od"]-1) if r["won"] else -1.0 for r in rows)/len(rows) if rows else 0.0
def med_of(rows, k):
    v = sorted(x[k] for x in rows if x.get(k) is not None)
    return v[len(v)//2] if v else None

MINN = 30
def build(U):
    C = []
    for k, lbl in (("od", "price"), ("cush", "cushion below median"), ("cushsd", "cushion in SDs"),
                   ("nq", "quotes tonight"), ("hrs", "hours before tip"), ("rest", "days rest"),
                   ("mins", "recent minutes"), ("sd", "her volatility")):
        m = med_of(U, k)
        if m is None: continue
        C.append((f"{lbl} HIGH", lambda r, k=k, m=m: r.get(k) is not None and r[k] >= m))
        C.append((f"{lbl} LOW",  lambda r, k=k, m=m: r.get(k) is not None and r[k] < m))
    for s in ("flip", "hotover", "overshoot"):
        C.append((f"src {s}", lambda r, s=s: r["src"] == s))
    for mk in ("pra", "pr", "pts"):
        C.append((f"market {mk}", lambda r, mk=mk: r["mk"] == mk))
    C.append(("tonight not raised (gate5)", lambda r: r["net"]))
    C.append(("tonight raised", lambda r: not r["net"]))
    return C
def sweep(U, name):
    C = build(U)
    bg = collections.defaultdict(list)
    for r in U: bg[(r["pl"], r["gt"])].append(r)
    keys = list(bg)
    res = []
    for lbl, sel in C:
        g = [r for r in U if sel(r)]
        if len(g) >= MINN: res.append((roiof(g), lbl, len(g)))
    res.sort(reverse=True)
    # game-block permutation: shuffle OUTCOMES between games, keep each game's bets together
    payload = [[(r["won"], r["od"]) for r in bg[k]] for k in keys]
    def best(assign):
        bb, bl = -9e9, ""
        idx = {}
        for k, pay in zip(keys, assign):
            for r, (w, o) in zip(bg[k], pay): idx[id(r)] = (w, o)
        for lbl, sel in C:
            g = [r for r in U if sel(r)]
            if len(g) < MINN: continue
            v = 100*sum((idx[id(r)][1]-1) if idx[id(r)][0] else -1.0 for r in g)/len(g)
            if v > bb: bb, bl = v, lbl
        return bb, bl
    real, rlbl = best(payload)
    T = 2000; beat = 0; sims = []
    for _ in range(T):
        random.shuffle(payload)
        v, _ = best(payload)
        sims.append(v)
        if v >= real: beat += 1
    sims.sort()
    print("")
    print("=" * 96)
    print(f"  {name}   {len(C)} cells, n>={MINN}")
    print("=" * 96)
    print(f"  NOISE CEILING FIRST: shuffled best-of-grid p95 = {sims[int(T*.95)]:+.1f}%  "
          f"(median {sims[T//2]:+.1f}%, max {sims[-1]:+.1f}%)")
    print(f"  best real cell: {rlbl} {real:+.1f}%   GAME-BLOCK p = {beat/T:.4f}")
    print("")
    base = roiof(U)
    print(f"  baseline (all {len(U)}): {base:+.1f}%")
    for v, lbl, n in res[:6]:
        mark = "  <- CLEARS CEILING" if v >= sims[int(T*.95)] else ""
        print(f"    {lbl:<32} n={n:<4} {v:+6.1f}%{mark}")
    print("    ...")
    for v, lbl, n in res[-3:]:
        print(f"    {lbl:<32} n={n:<4} {v:+6.1f}%")
sweep(A, "GATES 1+2 UNIVERSE")
sweep(S, "INSIDE MODEL S (gates 1+2+3)")
