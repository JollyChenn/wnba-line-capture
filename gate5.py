# gate5.py - is "tonight's line has not risen" a SUBSTITUTE for the star, or an addition to it?
# ---------------------------------------------------------------------------------------------
# Four questions, all on the same set, all at the PING price (the only one you can take):
#
#   1 was +18.6% measured with the filter ON? yes - gate 1 (3 signals) and gate 2 (pra/pr/pts) are
#     applied to everything below. What varies is gate 3 (the star, vs her PREVIOUS GAME) and the
#     proposed gate 5 (vs TONIGHT'S OPENING quote).
#
#   2 UP-THEN-DOWN. Ogunbowale went 18.5 -> 19.5 -> 17.5. My `moved` was last minus first, which
#     scores that as DOWN and ignores that the book raised her mid-window. Three definitions are
#     tested here because they disagree exactly on nights like that:
#       net     ping line <= opening line          (what I used - blind to the round trip)
#       nevup   the line NEVER went above the open (strictest)
#       ismin   the ping line is the lowest offered (you are being handed the best number)
#
#   3 RAW MODEL + gate 5. If gate 5 works because it measures the same inattention as the star,
#     only on a shorter clock, it might REPLACE gate 3 - which would let the no-previous-line
#     bets back in and recover volume.
#
#   4 THE NO-PREV GROUP. Those 64 bets ran -10.0% and are currently dropped because the star
#     cannot be evaluated without a previous number. Gate 5 needs no previous game at all, so it
#     CAN be evaluated on them. If it rescues them, the card gets meaningfully wider.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260923)
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

A = []
for r in load("graded_bets.csv"):
    if (r.get("result") or "").upper() not in ("WIN", "LOSS"): continue
    src, mk, pl = (r.get("src") or ""), (r.get("market") or ""), (r.get("player") or "").lower()
    if src not in SIGS or mk not in BET_MKTS: continue          # GATES 1 AND 2 ALWAYS ON
    tm = teamof.get(pl)
    gt = tip_on.get((tm, r.get("date") or "")) if tm else None
    if not gt: continue
    q = seq.get((pl, mk, gt), [])
    if len(q) < 2: continue
    now = pgrow.get((pl, gt))
    if not now: continue
    act = now[mk]
    o_l = q[0][1]; p_t, p_l, p_o = q[-1]
    if act == p_l: continue
    lines = [x[1] for x in q]
    pv = prevline.get((pl, mk, gt))
    star = "noprev" if pv is None else ("starred" if p_l - pv < 0.5 else "raised")
    A.append(dict(pl=pl, mk=mk, gt=gt, date=r.get("date"), src=src, act=act,
                  ln=p_l, od=p_o, won=act > p_l, star=star,
                  net=(p_l <= o_l), nevup=(max(lines) <= o_l), ismin=(p_l <= min(lines) + 1e-9),
                  moved=round(p_l - o_l, 1), peak=round(max(lines) - o_l, 1)))
best = {}
for r in sorted(A, key=lambda x: -x["od"]): best.setdefault((r["pl"], r["gt"]), r)
A = sorted(best.values(), key=lambda r: r["date"])
print(f"{len(A)} bets with gates 1+2 on, priced at the PING quote")
print(f"  star split: " + ", ".join(f"{k}:{v}" for k, v in collections.Counter(r['star'] for r in A).items()))
print("")

def sc(rows):
    n = len(rows); w = sum(1 for r in rows if r["won"])
    u = sum((r["od"]-1) if r["won"] else -1.0 for r in rows)
    return n, 100*w/n, u, 100*u/n
def pb(rows, T=3000):
    bp = collections.defaultdict(list)
    for r in rows: bp[r["pl"]].append(r)
    k = list(bp); o = []
    for _ in range(T):
        g = [x for p in [random.choice(k) for _ in k] for x in bp[p]]
        o.append(100*sum((x["od"]-1) if x["won"] else -1.0 for x in g)/len(g))
    o.sort(); return o[int(T*.025)], o[int(T*.975)]
def show(rows, label, minn=12):
    if len(rows) < minn: print(f"  {label:<42} n={len(rows)} too few"); return
    n, h, u, ro = sc(rows); lo, hi = pb(rows)
    print(f"  {label:<42} n={n:<4} {h:5.1f}%  {u:+6.2f}u  ROI {ro:+6.1f}%  95CI [{lo:+6.1f},{hi:+6.1f}]")

print("="*100)
print("  Q2. THE UP-THEN-DOWN CASE - three definitions of 'tonight has not raised her'")
print("="*100)
rt = [r for r in A if r["net"] and not r["nevup"]]
print(f"  round trips (went up, came back to or below the open): {len(rt)} of {len(A)}")
show(rt, "    the round trips themselves")
print("")
for k, lbl in (("net", "net: ping <= open (blind to the trip)"),
               ("nevup", "nevup: never went above the open"),
               ("ismin", "ismin: ping IS the lowest offered")):
    show([r for r in A if r[k]], f"  KEEP by {lbl}")
    show([r for r in A if not r[k]], f"    dropped by {lbl}")
    print("")
print("="*100)
print("  Q3/Q4. IS GATE 5 A SUBSTITUTE FOR THE STAR, OR AN ADDITION?")
print("="*100)
print(f"  {'':<26}{'gate5 PASS':>26}{'gate5 FAIL':>26}")
for stv in ("starred", "raised", "noprev"):
    g = [r for r in A if r["star"] == stv]
    p = [r for r in g if r["net"]]; q = [r for r in g if not r["net"]]
    def cell(x):
        if len(x) < 10: return f"n={len(x)} too few".rjust(26)
        n, h, u, ro = sc(x); return f"n={n:<3} {h:5.1f}%  ROI {ro:+6.1f}%".rjust(26)
    print(f"  gate3 = {stv:<18}{cell(p)}{cell(q)}")
print("")
print("  the diagonal is what matters: if gate 5 rescues the RAISED and NOPREV rows, it is doing")
print("  the star's job on a shorter clock and gate 3 could be replaced rather than stacked.")
print("")
print("="*100)
print("  THE CANDIDATE RULES, SIDE BY SIDE")
print("="*100)
show([r for r in A if r["star"] == "starred"],                  "  MODEL S today (gate 3 only)")
show([r for r in A if r["star"] == "starred" and r["net"]],     "  gate 3 AND gate 5 (stacked)")
show([r for r in A if r["net"]],                                "  gate 5 ONLY (raw model + tonight)")
show([r for r in A if r["net"] and r["star"] != "raised"],      "  gate 5, allow noprev, drop raised")
show(A,                                                          "  no star gate at all (raw)")
print("")
print("="*100)
print("  VOLUME")
print("="*100)
tot = len({r["date"] for r in A})
for lbl, g in (("MODEL S today", [r for r in A if r["star"] == "starred"]),
               ("gate 3 + gate 5", [r for r in A if r["star"] == "starred" and r["net"]]),
               ("gate 5 only", [r for r in A if r["net"]])):
    print(f"  {lbl:<24} {len(g):>4} bets over {tot} slates = {len(g)/tot:.2f} a night")
