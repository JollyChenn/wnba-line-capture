# xm_overlap.py - STEP 2: overlap matrix, contradictions, who wins a disagreement.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])

L = load("bets_log.csv")
FIRE = {}
for r in L:
    pl = (r.get("player") or "").lower(); mk = r.get("market"); sd = r.get("side")
    src = r.get("src") or ""; ln = f(r.get("line")); od = f(r.get("odds")); cap = ts(r.get("captured_utc"))
    if not (pl and mk and sd and cap and ln is not None): continue
    tm = teamof.get(pl)
    if not tm: continue
    gt = game_for(tm, cap)
    if not gt: continue
    k = (src, pl, mk, gt)
    cur = FIRE.get(k)
    if cur is None or cap < cur["cap"]:
        FIRE[k] = dict(src=src, pl=pl, mk=mk, gt=gt, side=sd, line=ln, odds=od, cap=cap,
                       tier=r.get("tier"), ev=f(r.get("ev")), pinn=f(r.get("pinn")), date=r.get("date"))

# settle each fire at its OWN captured board price (real one-sided board quote at that instant)
def settle(v):
    row = pgrow.get((v["pl"], v["gt"]))
    if not row: return None
    act = row.get(v["mk"])
    if act is None or v["odds"] is None: return None
    if act == v["line"]: return None                      # push
    won = (act > v["line"]) if v["side"] == "Over" else (act < v["line"])
    return dict(act=act, won=won, pnl=(v["odds"]-1) if won else -1.0)

R = {}
for k, v in FIRE.items():
    s = settle(v)
    if s: R[k] = dict(v, **s)
print(f"settled fires: {len(R)}")

SRCS = [s for s, _ in collections.Counter(k[0] for k in R).most_common()]

# ---- per-family baseline, priced at its own real board odds ----------------------------------
print("\n=== FAMILY BASELINES (own captured board price, no push) ===")
print(f"{'src':<12}{'n':>5}{'win%':>8}{'ROI%':>9}{'CI95':>20}{'avg odds':>10}")
def ci(pnls):
    n = len(pnls)
    if n < 2: return (float('nan'), float('nan'))
    m = statistics.mean(pnls); sd = statistics.pstdev(pnls)
    h = 1.96*sd/math.sqrt(n)
    return (100*(m-h), 100*(m+h))
FAM = collections.defaultdict(list)
for k, v in R.items(): FAM[k[0]].append(v)
for s in SRCS:
    rows = FAM[s]; p = [r["pnl"] for r in rows]
    lo, hi = ci(p)
    print(f"{s:<12}{len(rows):>5}{100*sum(r['won'] for r in rows)/len(rows):>7.1f}%"
          f"{100*statistics.mean(p):>8.1f}%   [{lo:>6.1f},{hi:>6.1f}]"
          f"{statistics.mean(r['odds'] for r in rows):>9.2f}")

# ---- OVERLAP MATRIX at player-game level ------------------------------------------------------
pg = collections.defaultdict(set)          # (pl,gt) -> set of src
pgm = collections.defaultdict(set)         # (pl,mk,gt) -> set of src
pg_side = collections.defaultdict(dict)    # (pl,gt) -> {src: side}
for k, v in R.items():
    pg[(v["pl"], v["gt"])].add(v["src"])
    pgm[(v["pl"], v["mk"], v["gt"])].add(v["src"])
    pg_side[(v["pl"], v["gt"])][v["src"]] = v["side"]

MAIN = [s for s in SRCS if len(FAM[s]) >= 15]
print("\n=== OVERLAP MATRIX: player-games where BOTH families fired ===")
print("     (row header n = player-games that family touched)")
own = {s: sum(1 for k, v in pg.items() if s in v) for s in MAIN}
hdr = "".join(f"{s[:9]:>11}" for s in MAIN)
print(f"{'':<12}{'own':>6}{hdr}")
OV = {}
for a in MAIN:
    line = f"{a:<12}{own[a]:>6}"
    for b in MAIN:
        n = sum(1 for k, v in pg.items() if a in v and b in v)
        OV[(a,b)] = n
        line += f"{n:>11}" if a != b else f"{'-':>11}"
    print(line)

print("\n=== JACCARD (player-game level) - redundancy ranking ===")
J = []
for i, a in enumerate(MAIN):
    for b in MAIN[i+1:]:
        inter = OV[(a,b)]; uni = own[a] + own[b] - inter
        if uni: J.append((inter/uni, a, b, inter, own[a], own[b]))
for j, a, b, inter, na, nb in sorted(J, reverse=True)[:12]:
    print(f"  {a:<12} x {b:<12} J={j:.3f}  shared {inter:>3}  ({inter/na:.0%} of {a}, {inter/nb:.0%} of {b})")

# same MARKET too (a true duplicate bet)
print("\n=== SAME player+market+game (identical bet slot) ===")
J2 = []
own2 = {s: sum(1 for k, v in pgm.items() if s in v) for s in MAIN}
for i, a in enumerate(MAIN):
    for b in MAIN[i+1:]:
        inter = sum(1 for k, v in pgm.items() if a in v and b in v)
        if inter == 0: continue
        uni = own2[a] + own2[b] - inter
        J2.append((inter/uni, a, b, inter, own2[a], own2[b]))
for j, a, b, inter, na, nb in sorted(J2, reverse=True):
    print(f"  {a:<12} x {b:<12} J={j:.3f}  shared {inter:>3}  ({inter/na:.0%} of {a}, {inter/nb:.0%} of {b})")

# ---- CONTRADICTIONS ---------------------------------------------------------------------------
print("\n=== CONTRADICTIONS: same player-game, opposite sides ===")
cc = collections.Counter(); cwin = collections.Counter()
contra_pgs = []
for k, sides in pg_side.items():
    ov = [s for s, sd in sides.items() if sd == "Over"]
    un = [s for s, sd in sides.items() if sd == "Under"]
    if ov and un:
        contra_pgs.append((k, ov, un))
        for a in ov:
            for b in un: cc[(a,b)] += 1
print(f"contradicted player-games: {len(contra_pgs)} of {len(pg)}")
for (a,b), n in cc.most_common(15): print(f"  OVER {a:<12} vs UNDER {b:<12} {n:>4}")

# who wins? grade both fires at their own price
print("\n=== WHO WINS A CONTRADICTION (each fire at its own board price) ===")
ovp, unp = [], []
for (k, ov, un) in contra_pgs:
    pl, gt = k
    for kk, v in R.items():
        if v["pl"] == pl and v["gt"] == gt:
            (ovp if v["side"] == "Over" else unp).append(v["pnl"])
for lbl, p in (("OVER side in a contradiction", ovp), ("UNDER side in a contradiction", unp)):
    lo, hi = ci(p)
    print(f"  {lbl:<32} n={len(p):>4}  ROI {100*statistics.mean(p):>6.1f}%  CI[{lo:>6.1f},{hi:>6.1f}]")
# control: same families when NOT contradicted
print("\n  control - same fires on UNcontradicted player-games:")
cset = {k for k, _, _ in contra_pgs}
ovc = [v["pnl"] for v in R.values() if v["side"]=="Over" and (v["pl"],v["gt"]) not in cset]
unc = [v["pnl"] for v in R.values() if v["side"]=="Under" and (v["pl"],v["gt"]) not in cset]
for lbl, p in (("OVER, no contradiction", ovc), ("UNDER, no contradiction", unc)):
    lo, hi = ci(p)
    print(f"  {lbl:<32} n={len(p):>4}  ROI {100*statistics.mean(p):>6.1f}%  CI[{lo:>6.1f},{hi:>6.1f}]")
