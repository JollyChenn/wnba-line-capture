# basis_check.py - was the OPEN/PING gap real, or did I build it myself?
# ---------------------------------------------------------------------------------------------
# pricedecay.py shows a FLAT curve on a frozen bet set: 36h +11.2% ... 1h +14.5%, same mean line,
# same mean odds. If price alone were eating 9 points of ROI, that curve would slope. It does not.
#
# So where did OPEN +12.8% / PING +4.0% come from? Suspicion: ping_vs_open.py:56 applies gate 3
# using `o_ln` - the line in graded_bets, which is the OPENING number - and then prices the bet at
# the PING. Gate evaluated at one moment, bet placed at another. That combination lets in exactly
# the bets the card would have thrown out by ping time: the ones the book RAISED after it opened.
# The card never sees those. If they are the drag, the +4.0% is an artifact of my own script and
# not a property of the market.
#
# Three columns, same bets, so the leak has nowhere to hide:
#   gate@open  price@open   what every historical ROI in this repo reports
#   gate@open  price@ping   what ping_vs_open.py reported as "what you can take"  <- suspect
#   gate@ping  price@ping   what the CARD actually does
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
tip_on = {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    tip_on[(hm, d2)] = t2; tip_on[(aw, d2)] = t2

R = []
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
    pv = prevline.get((pl, mk, gt))
    if pv is None: continue
    act = now[mk]
    o_t, o_l, o_o = q[0]; p_t, p_l, p_o = q[-1]
    if act == o_l or act == p_l: continue
    R.append(dict(pl=pl, mk=mk, gt=gt, date=r.get("date"), src=src, act=act, prev=pv,
                  o_l=o_l, o_o=o_o, o_w=act > o_l, p_l=p_l, p_o=p_o, p_w=act > p_l,
                  pass_open=(o_l - pv < 0.5), pass_ping=(p_l - pv < 0.5),
                  moved=round(p_l - o_l, 1)))
def dedupe(rows, ok):
    best = {}
    for r in sorted(rows, key=lambda x: -x[ok]): best.setdefault((r["pl"], r["gt"]), r)
    return list(best.values())
def sc(rows, wk, ok):
    n = len(rows); w = sum(1 for r in rows if r[wk])
    u = sum((r[ok]-1) if r[wk] else -1.0 for r in rows)
    return n, 100*w/n, u, 100*u/n
def show(rows, lbl, wk, ok, minn=10):
    if len(rows) < minn: print(f"  {lbl:<50} n={len(rows)} too few"); return
    n, h, u, ro = sc(rows, wk, ok)
    print(f"  {lbl:<50} n={n:<4}{h:>6.1f}%{u:>+8.2f}u{ro:>+8.1f}%")

A = [r for r in R if r["pass_open"]]
B_ = [r for r in R if r["pass_ping"]]
print("="*104)
print("  THE THREE COMBINATIONS")
print("="*104)
show(dedupe(A, "o_o"),  "gate@OPEN  price@OPEN   (every historical ROI here)", "o_w", "o_o")
show(dedupe(A, "p_o"),  "gate@OPEN  price@PING   (ping_vs_open.py's +4.0%)", "p_w", "p_o")
show(dedupe(B_, "p_o"), "gate@PING  price@PING   (what the CARD does)", "p_w", "p_o")
print("")
print("="*104)
print("  THE LEAK - bets that pass at open but the card would REJECT at ping")
print("="*104)
leak = [r for r in R if r["pass_open"] and not r["pass_ping"]]
keep = [r for r in R if r["pass_open"] and r["pass_ping"]]
gain = [r for r in R if r["pass_ping"] and not r["pass_open"]]
show(dedupe(leak, "p_o"), "  IN ping_vs_open, NOT on the card (book raised her)", "p_w", "p_o")
show(dedupe(keep, "p_o"), "  in both", "p_w", "p_o")
show(dedupe(gain, "p_o"), "  on the card, NOT in ping_vs_open (book cut her)", "p_w", "p_o")
print("")
print("  the leak group is priced at the ping but was selected on a number that no longer exists.")
print("  the card has never bet one of these and never will.")
print("")
print("="*104)
print("  SAMPLE RECONCILIATION - why 85 and not 75")
print("="*104)
print(f"  graded rows passing gates 1+2, with board history + box + a previous line : {len(R)}")
print(f"    of those, gate 3 passes at the OPEN line                                : {len(dedupe(A,'o_o'))}")
print(f"    of those, gate 3 passes at the PING line                                : {len(dedupe(B_,'p_o'))}")
print(f"    pass at open but not ping (raised late)                                 : {len(dedupe(leak,'p_o'))}")
print(f"    pass at ping but not open (cut late)                                    : {len(dedupe(gain,'p_o'))}")
