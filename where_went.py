# where_went.py - the backtest says ~+20%. The live tracker says -1.0%. Reconcile them.
import csv, os, sys, math, random, collections, datetime, statistics
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260925)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "gate5.py"), encoding="utf-8").read()
     .split('print(f"{len(A)} bets with gates 1+2 on')[0])

mf = [r for r in load("model_forward.csv") if (r.get("result") or "").upper() in ("WIN", "LOSS")]
print(f"THE 13 BETS THE CARD ACTUALLY PUT IN FRONT OF YOU")
print("=" * 96)
print(f"  {'player':<20}{'mk':<5}{'line':>6}{'odds':>7}  {'res':<6}{'tonight open->now':>20}  gate5")
tot = 0.0; g5p = []; g5f = []
for r in mf:
    pl, mk = (r.get("player") or "").lower(), r.get("market")
    tip = ts(r.get("tip")); ln, od = f(r.get("line")), f(r.get("odds"))
    won = (r.get("result") or "").upper() == "WIN"
    u = (od - 1) if won else -1.0
    tot += u
    q = seq.get((pl, mk, tip), [])
    if q:
        o_l, p_l = q[0][1], q[-1][1]
        ok = p_l <= o_l
        (g5p if ok else g5f).append(u)
        mv = f"{o_l} -> {p_l}"
        v = "PASS" if ok else "FAIL"
    else:
        mv, v = "no history", "?"
    print(f"  {(r.get('player') or '')[:19]:<20}{mk:<5}{ln!s:>6}{od!s:>7}  {('WIN' if won else 'loss'):<6}{mv:>20}  {v}")
print("")
print(f"  TOTAL  {len(mf)} bets  {sum(1 for r in mf if (r.get('result') or '').upper()=='WIN')}W-"
      f"{sum(1 for r in mf if (r.get('result') or '').upper()=='LOSS')}L  {tot:+.2f}u  ROI {100*tot/len(mf):+.1f}%")
if g5p: print(f"    of which gate5 PASS: n={len(g5p)}  {sum(g5p):+.2f}u  ROI {100*sum(g5p)/len(g5p):+.1f}%")
if g5f: print(f"    of which gate5 FAIL: n={len(g5f)}  {sum(g5f):+.2f}u  ROI {100*sum(g5f)/len(g5f):+.1f}%")
print("")
print("=" * 96)
print("  IS -1.0% ON 13 BETS EVEN INCONSISTENT WITH A TRUE +20%?")
print("=" * 96)
n = len(mf); w = sum(1 for r in mf if (r.get("result") or "").upper() == "WIN")
for p, lbl in ((0.673, "true 67.3% (the gate3+gate5 cell)"), (0.640, "true 64.0% (gate3 only)"),
               (0.538, "true 53.8% (break-even-ish)")):
    exp = n * p; sd = math.sqrt(n * p * (1 - p))
    z = (w - exp) / sd
    print(f"  {lbl:<38} expect {exp:.1f}W of {n}, saw {w}W   z = {z:+.2f}")
print("")
print(f"  a 95% band on {n} bets is roughly +/-{100*1.96*0.5/math.sqrt(n):.0f} points of hit rate.")
print("  nothing in this sample can separate a 67% model from a coin.")
print("")
print("=" * 96)
print("  SO WHERE IS THE ~20%? IT WAS NEVER REALISED MONEY.")
print("=" * 96)
star = [r for r in A if r["star"] == "starred"]
stack = [r for r in A if r["star"] == "starred" and r["net"]]
def sc(rows):
    n_ = len(rows); w_ = sum(1 for r in rows if r["won"])
    u_ = sum((r["od"]-1) if r["won"] else -1.0 for r in rows)
    return n_, 100*w_/n_, u_, 100*u_/n_
for lbl, g in (("gate3 only, ping price", star), ("gate3+gate5, ping price", stack)):
    n_, h_, u_, r_ = sc(g)
    print(f"  {lbl:<34} n={n_:<4} {h_:5.1f}%  {u_:+7.2f}u  ROI {r_:+6.1f}%")
print(f"  {'the card LIVE (real recommendations)':<34} n={len(mf):<4} "
      f"{100*w/len(mf):5.1f}%  {tot:+7.2f}u  ROI {100*tot/len(mf):+6.1f}%")
print("")
ov = {(r["pl"], r["gt"]) for r in A}
liveset = {((r.get("player") or "").lower(), ts(r.get("tip"))) for r in mf}
print(f"  overlap between the backtest set and the live 13: {len(ov & liveset)} bets")
print("  the backtest bets were RECONSTRUCTED from logs after the fact; the 13 were pinged.")
