# gateladder.py - signal alone, or signal plus gates? Which gates are actually load-bearing?
# ---------------------------------------------------------------------------------------------
# "Filter" and "gate" are doing different jobs and it is worth separating them cleanly:
#
#   THE FILTER   is the SIGNAL - flip, hotover, overshoot. It decides that a player's over line is
#                mispriced at all. Without it there is no bet to make.
#   THE GATES    do not find anything. They only remove. gate 2 removes markets, gate 3 removes
#                bets the book has already repriced, gate 4 removes duplicate positions.
#
# So the question "is it still profitable with only the filter and no gates" has a precise form:
# take every bet the three signals ever produced, drop every gate, and see what it returns.
#
# Two views, because cumulative ladders hide which gate is doing the work:
#   CUMULATIVE     add gates one at a time - shows the path from raw signal to Model S
#   LEAVE ONE OUT  Model S with exactly one gate switched off - shows what each gate is worth on
#                  its own, given the others are already there. A gate that changes nothing here
#                  is decoration, however good the cumulative ladder makes it look.
#
# Everything is priced at the ping with gate 3 judged at the ping, per basis_check.py - gate and
# price read at the same instant, which is the rule that would have prevented yesterday's error.
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
tip_on, gof = {}, {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    tip_on[(hm, d2)] = t2; tip_on[(aw, d2)] = t2
    gof[(hm, t2)] = gid; gof[(aw, t2)] = gid

U = []
for r in load("graded_bets.csv"):
    if (r.get("result") or "").upper() not in ("WIN", "LOSS"): continue
    src, mk, pl = (r.get("src") or ""), (r.get("market") or ""), (r.get("player") or "").lower()
    side = r.get("side") or "Over"
    tm = teamof.get(pl)
    gt = tip_on.get((tm, r.get("date") or "")) if tm else None
    if not gt: continue
    now = pgrow.get((pl, gt))
    q = seq.get((pl, mk, gt), [])
    if not now or mk not in now or len(q) < 2: continue
    p_t, p_l, p_o = q[-1]
    if now[mk] == p_l: continue
    pv = prevline.get((pl, mk, gt))
    U.append(dict(pl=pl, mk=mk, gt=gt, gid=gof[(tm, gt)], date=r.get("date"), src=src, side=side,
                  ln=p_l, od=p_o, won=now[mk] > p_l,
                  g1=(src in SIGS), g2=(mk in BET_MKTS),
                  g3=(pv is not None and p_l - pv < 0.5)))
print(f"{len(U)} settled bets measurable at the ping (board history + box score)")
print("")

def dedupe(rows):
    best = {}
    for r in sorted(rows, key=lambda x: -x["od"]): best.setdefault((r["pl"], r["gt"]), r)
    return list(best.values())
def sc(rows):
    n = len(rows); w = sum(1 for r in rows if r["won"])
    u = sum((r["od"]-1) if r["won"] else -1.0 for r in rows)
    return n, 100*w/n, u, 100*u/n
def gboot(rows, T=3000):
    bg = collections.defaultdict(list)
    for r in rows: bg[r["gid"]].append(r)
    k = list(bg); o = []
    for _ in range(T):
        g = [x for p in [random.choice(k) for _ in k] for x in bg[p]]
        o.append(100*sum((x["od"]-1) if x["won"] else -1.0 for x in g)/len(g))
    o.sort(); return o[int(T*.025)], o[int(T*.975)]
def show(rows, lbl, minn=10):
    if len(rows) < minn: print(f"  {lbl:<48} n={len(rows)} too few"); return
    n, h, u, ro = sc(rows); lo, hi = gboot(rows)
    flag = "  <-- LOSES" if ro < 0 else ("" if lo < 0 else "  <-- CI clears zero")
    print(f"  {lbl:<48} n={n:<4}{h:>6.1f}%{u:>+9.2f}u{ro:>+8.1f}%  95CI [{lo:+6.1f},{hi:+6.1f}]{flag}")

print("="*112)
print("  CUMULATIVE - from raw signal to Model S")
print("="*112)
s1 = [r for r in U if r["g1"]]
s2 = [r for r in s1 if r["g2"]]
s3 = [r for r in s2 if r["g3"]]
s4 = dedupe(s3)
show(U,  "  no filter, no gates - everything logged")
show(s1, "  FILTER ONLY: flip/hotover/overshoot, no gates")
show(s2, "    + gate 2 (pra/pr/pts)")
show(s3, "    + gate 3 (book has not raised her)")
show(s4, "    + gate 4 (one position per player) = MODEL S")
print("")
print("="*112)
print("  LEAVE ONE OUT - Model S with exactly one gate switched off")
print("="*112)
show(s4, "  MODEL S, all gates on")
show(dedupe([r for r in U  if r["g2"] and r["g3"]]),  "  gate 1 OFF (any src)")
show(dedupe([r for r in s1 if r["g3"]]),              "  gate 2 OFF (any market)")
show(dedupe([r for r in s2]),                          "  gate 3 OFF (raised allowed)")
show([r for r in s3],                                  "  gate 4 OFF (duplicate positions kept)")
print("")
print("="*112)
print("  WHAT EACH GATE THROWS AWAY - a gate only earns its place if its REJECTS are worse")
print("="*112)
show(dedupe([r for r in U  if not r["g1"] and r["g2"] and r["g3"]]), "  rejected by gate 1")
show(dedupe([r for r in s1 if not r["g2"] and r["g3"]]),             "  rejected by gate 2")
show(dedupe([r for r in s2 if not r["g3"]]),                          "  rejected by gate 3")
print("")
print("="*112)
print("  THE FILTER ALONE, BY SIGNAL - no gates at all")
print("="*112)
for s in SIGS: show([r for r in s1 if r["src"] == s], f"  {s}")
print("")
print("="*112)
print("  SANITY: is the signal even picking the right SIDE?")
print("="*112)
for sd in ("Over", "Under"):
    show([r for r in s1 if r["side"] == sd], f"  filter only, {sd} bets")
