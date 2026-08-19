# pricedecay.py - WHY does +12.8% at the open become +4.0% at the ping, and where is the money?
# ---------------------------------------------------------------------------------------------
# ping_vs_open.py established the gap. It did not explain it, and "the price basis is wrong" is a
# diagnosis, not a fix. Three competing explanations, and they imply completely different actions:
#
#   A  THE OPEN IS SIMPLY BETTER AND WE PING TOO LATE.  The book posts a soft number 40h out and
#      sharpens it as tip approaches. Then the fix is to ping EARLIER, not to filter.
#   B  THE LATE MOVE IS INFORMATION.  The line drops because her minutes are being cut, a starter
#      is back, she is on a minutes limit. The lower number is lower for a reason and the over at
#      that number is fairly priced. Then the open's edge is unreachable - it is a number nobody
#      would still be offering by the time we could act on it.
#   C  COMPOSITION.  Different bets survive the gates at different horizons, so the two ROIs are
#      not measured on the same bets at all and the "decay" is a selection artifact.
#
# The test that separates them is a HORIZON CURVE, run two ways:
#   REALISTIC   at each horizon H, re-evaluate the gates using the line on offer at H, and bet
#               whatever passes. This is literally "what if the card pinged at H hours out".
#   CONSTANT    only the bets that pass at EVERY horizon, priced at each horizon in turn. The bet
#               set is frozen, so anything left is pure price and cannot be composition (kills C).
#
# If the curve slopes down in BOTH, the open is genuinely better and we are pinging too late (A).
# If it slopes down only in REALISTIC, it is composition (C).
# If it is FLAT in CONSTANT but down-moves still win, the move is information (B).
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260819)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
SIGS = ("flip", "hotover", "overshoot"); BET_MKTS = ("pra", "pr", "pts")
HORIZ = [48, 36, 30, 24, 18, 12, 9, 6, 4, 2, 1]

# every Over quote for a player-market-game, in time order
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

tip_on = {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    tip_on[(hm, d2)] = t2; tip_on[(aw, d2)] = t2

# the forward-selected signal set: gates 1 and 2, before any price or star logic
CAND = []
for r in load("graded_bets.csv"):
    if (r.get("result") or "").upper() not in ("WIN", "LOSS"): continue
    src, mk, pl = (r.get("src") or ""), (r.get("market") or ""), (r.get("player") or "").lower()
    if src not in SIGS or mk not in BET_MKTS: continue
    tm = teamof.get(pl)
    gt = tip_on.get((tm, r.get("date") or "")) if tm else None
    if not gt: continue
    q = seq.get((pl, mk, gt), [])
    now = pgrow.get((pl, gt))
    if len(q) < 2 or not now: continue
    CAND.append(dict(pl=pl, mk=mk, gt=gt, date=r.get("date"), src=src, act=now[mk], q=q,
                     prev=prevline.get((pl, mk, gt))))
# one row per player-market-game
uniq = {}
for c in CAND: uniq[(c["pl"], c["mk"], c["gt"])] = c
CAND = list(uniq.values())
print(f"{len(CAND)} signal candidates (gates 1+2) with a board history and a box score")
print("")

def at(c, H):
    """the last quote at or before H hours to tip - what the card would have seen then"""
    cut = c["gt"] - datetime.timedelta(hours=H)
    got = [x for x in c["q"] if x[0] <= cut]
    return got[-1] if got else None

def bets_at(H):
    """re-run gates 3 and 4 on the line that existed at horizon H"""
    out = []
    for c in CAND:
        s = at(c, H)
        if not s: continue
        t, ln, od = s
        if c["prev"] is None or ln - c["prev"] >= 0.5: continue        # gate 3, judged at H
        if c["act"] == ln: continue                                     # push
        out.append(dict(c, ln=ln, od=od, won=c["act"] > ln, H=H))
    best = {}
    for r in sorted(out, key=lambda x: -x["od"]): best.setdefault((r["pl"], r["gt"]), r)   # gate 4
    return list(best.values())

def sc(rows):
    n = len(rows); w = sum(1 for r in rows if r["won"])
    u = sum((r["od"]-1) if r["won"] else -1.0 for r in rows)
    return n, 100*w/n, u, 100*u/n
def pb(rows, T=2500):
    bp = collections.defaultdict(list)
    for r in rows: bp[r["pl"]].append(r)
    k = list(bp); o = []
    for _ in range(T):
        g = [x for p in [random.choice(k) for _ in k] for x in bp[p]]
        o.append(100*sum((x["od"]-1) if x["won"] else -1.0 for x in g)/len(g))
    o.sort(); return o[int(T*.025)], o[int(T*.975)]

print("="*104)
print("  REALISTIC - what pinging at H hours to tip would actually have given you")
print("="*104)
print(f"  {'H to tip':<12}{'n':>5}{'hit%':>8}{'units':>9}{'ROI':>9}   {'95% CI (player-block)':<26}{'mean line':>10}")
REAL = {}
for H in HORIZ:
    rows = bets_at(H); REAL[H] = rows
    if len(rows) < 15: print(f"  {H:>3}h        n={len(rows)} too few"); continue
    n, h, u, ro = sc(rows); lo, hi = pb(rows)
    ml = statistics.mean(r["ln"] for r in rows)
    print(f"  {H:>3}h {'':<7}{n:>5}{h:>7.1f}%{u:>+9.2f}{ro:>+8.1f}%   [{lo:+6.1f},{hi:+6.1f}]{'':<10}{ml:>10.2f}")
print("")

# the constant set: passes gate 3 and is quoted at EVERY horizon. 48h is excluded from the
# INTERSECTION (only 1 bet is quoted that early, which would empty it) but still reported above.
HZ2 = [h for h in HORIZ if len(REAL[h]) >= 15]
keys = None
for H in HZ2:
    s = {(r["pl"], r["mk"], r["gt"]) for r in REAL[H]}
    keys = s if keys is None else (keys & s)
HORIZ = HZ2
print("="*104)
print("  CONSTANT SET - the same bets at every horizon. Any slope here is PURE PRICE.")
print("="*104)
print(f"  {len(keys)} bets pass the gates and are quoted at all {len(HORIZ)} horizons")
print(f"  {'H to tip':<12}{'n':>5}{'hit%':>8}{'units':>9}{'ROI':>9}   {'95% CI':<22}{'mean line':>10}{'mean odds':>11}")
for H in HORIZ:
    rows = [r for r in REAL[H] if (r["pl"], r["mk"], r["gt"]) in keys]
    if len(rows) < 15: print(f"  {H:>3}h        n={len(rows)} too few"); continue
    n, h, u, ro = sc(rows); lo, hi = pb(rows)
    ml = statistics.mean(r["ln"] for r in rows); mo = statistics.mean(r["od"] for r in rows)
    print(f"  {H:>3}h {'':<7}{n:>5}{h:>7.1f}%{u:>+9.2f}{ro:>+8.1f}%   [{lo:+6.1f},{hi:+6.1f}]{'':<6}{ml:>10.2f}{mo:>11.3f}")
print("")

print("="*104)
print("  IS THE LATE MOVE INFORMATION? - grade at the PING line, split by how the line moved")
print("="*104)
P = REAL[HORIZ[-1]] if len(REAL[HORIZ[-1]]) >= 15 else REAL[6]
mvd = []
for r in P:
    o = at(r, 48) or r["q"][0]
    mvd.append(dict(r, mv=round(r["ln"] - o[1], 1), resid=r["act"] - r["ln"]))
buck = collections.defaultdict(list)
for r in mvd:
    k = "line CUT (-1.0 or more)" if r["mv"] <= -1.0 else \
        "line cut (-0.5)"         if r["mv"] <= -0.5 else \
        "unchanged"               if abs(r["mv"]) < 0.5 else \
        "line raised (+0.5)"      if r["mv"] < 1.0 else "line RAISED (+1.0 or more)"
    buck[k].append(r)
print(f"  {'move from 48h out':<30}{'n':>5}{'hit%':>8}{'ROI':>9}{'mean resid':>13}")
for k in ("line CUT (-1.0 or more)", "line cut (-0.5)", "unchanged",
          "line raised (+0.5)", "line RAISED (+1.0 or more)"):
    g = buck.get(k, [])
    if len(g) < 8: print(f"  {k:<30}n={len(g)} too few"); continue
    n, h, u, ro = sc(g)
    print(f"  {k:<30}{n:>5}{h:>7.1f}%{ro:>+8.1f}%{statistics.mean(x['resid'] for x in g):>+13.2f}")
print("")
print("  mean resid = actual minus the line we bet. If the book's late move were pure information,")
print("  every bucket would sit near the same residual - the move would already be priced in.")
print("")
print("="*104)
print("  HOW MUCH DOES THE NUMBER ACTUALLY MOVE?")
print("="*104)
allmv = collections.Counter(r["mv"] for r in mvd)
print("  48h -> ping: " + ", ".join(f"{k:+.1f}:{v}" for k, v in sorted(allmv.items())))
print(f"  unchanged on {sum(v for k, v in allmv.items() if abs(k) < 0.25)} of {len(mvd)}")
