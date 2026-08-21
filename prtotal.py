# prtotal.py - PR escapes the engine's low-total guard. Should it?
# ---------------------------------------------------------------------------------------------
# cloud_xbet.py:411 splits the markets two ways:
#     TOTAL_TRAP = {"pts", "pra"}          dropped when the team total is low
#     TOTAL_SAFE = {"pa", "ra", "ast", "reb"}   kept, on the theory that rebounds rise on misses
#                                               and assists are flat
# "pr" is in NEITHER set, so it is never dropped - and pr is points PLUS rebounds, which is about
# as points-heavy as pra. It is also 38% of Model S in backtest and 62% of the live card. If pr
# behaves like the traps, the guard has a hole in the market it fires on most.
#
# shade2.py already showed the SAFE half is not safe at all - low-total games cost reb/ast/ra/pa
# overs 4.1 points against 5.3 for pts/pra, which is the same number. This checks pr directly and
# then reads tonight's board-implied total, because both of tonight's bets are PR and PRA.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260820)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
ALLMK = ("pts", "pr", "pra", "pa", "ra", "reb", "ast")
gof, oppof, dateof = {}, {}, {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    gof[(hm, t2)] = gid; gof[(aw, t2)] = gid
    oppof[(hm, t2)] = aw; oppof[(aw, t2)] = hm
    dateof[t2] = d2
_mc = {}
def med_team(pl, mk, gt):
    k = (pl, mk, gt)
    if k in _mc: return _mc[k]
    g = [r for r in hist.get(pl, []) if r["tip"] < gt]
    out = None
    if g:
        cur = g[-1]["tm"]; g = [r for r in g if r["tm"] == cur]
        if len(g) >= 5: out = statistics.median([r[mk] for r in g[-10:]])
    _mc[k] = out
    return out
ptsline = collections.defaultdict(list)
for (pl, mk, gt), sdq in side.items():
    if mk == "pts" and "Over" in sdq and teamof.get(pl):
        ptsline[(teamof[pl], gt)].append(sdq["Over"][1])

Q = []
for (pl, mk, gt), sdq in side.items():
    if mk not in ALLMK or "Over" not in sdq or "Under" not in sdq: continue
    if abs(sdq["Over"][1] - sdq["Under"][1]) > 0.01: continue
    now = pgrow.get((pl, gt)); tm = teamof.get(pl)
    if not now or mk not in now or not tm: continue
    ln = sdq["Over"][1]
    if now[mk] == ln: continue
    a, b = ptsline.get((tm, gt), []), ptsline.get((oppof.get((tm, gt)), gt), [])
    if len(a) < 4 or len(b) < 4: continue
    md = med_team(pl, mk, gt)
    Q.append(dict(pl=pl, mk=mk, gid=gof[(tm, gt)], tm=tm, ln=ln, btot=sum(a)+sum(b),
                  o_od=sdq["Over"][2], o_won=now[mk] > ln,
                  cush=(md - ln) if md is not None else None))
v = sorted(r["btot"] for r in Q); lo3, hi3 = v[len(v)//3], v[2*len(v)//3]
def roi(rows): return 100*sum((r["o_od"]-1) if r["o_won"] else -1.0 for r in rows)/len(rows) if rows else 0
def hit(rows): return 100*sum(1 for r in rows if r["o_won"])/len(rows) if rows else 0
print(f"{len(Q)} overs with a board-implied total; terciles {lo3:.0f} / {hi3:.0f}")
print("")
print("="*96)
print("  EVERY MARKET'S SENSITIVITY TO THE GAME TOTAL (over side)")
print("="*96)
print(f"  {'market':<8}{'engine treats as':<20}{'LOW total':>20}{'HIGH total':>20}{'swing':>9}")
ENG = {"pts": "TRAP (dropped)", "pra": "TRAP (dropped)", "pr": "-- neither --",
       "pa": "SAFE (kept)", "ra": "SAFE (kept)", "reb": "SAFE (kept)", "ast": "SAFE (kept)"}
rank = []
for m in ALLMK:
    lo_ = [r for r in Q if r["mk"] == m and r["btot"] <= lo3]
    hi_ = [r for r in Q if r["mk"] == m and r["btot"] > hi3]
    if len(lo_) < 20 or len(hi_) < 20: continue
    sw = roi(hi_) - roi(lo_); rank.append((sw, m))
    print(f"  {m:<8}{ENG[m]:<20}"
          f"{('n=%d %+.1f%%' % (len(lo_), roi(lo_))):>20}{('n=%d %+.1f%%' % (len(hi_), roi(hi_))):>20}{sw:>+9.1f}")
rank.sort(reverse=True)
print("")
print("  most total-sensitive to least: " + " > ".join(m for _, m in rank))
print("")
print("="*96)
print("  THE THREE MODEL S MARKETS IN LOW-TOTAL GAMES, DEEP CUSHION ONLY")
print("="*96)
for m in ("pts", "pr", "pra"):
    for lbl, sel in (("LOW  total", lambda r: r["btot"] <= lo3), ("HIGH total", lambda r: r["btot"] > hi3)):
        g = [r for r in Q if r["mk"] == m and r["cush"] is not None and r["cush"] >= 3 and sel(r)]
        if len(g) < 15: print(f"    {m:<5} {lbl}  n={len(g)} too few"); continue
        print(f"    {m:<5} {lbl}  n={len(g):<4}{hit(g):>6.1f}%{roi(g):>+8.1f}%")
    print("")
print("="*96)
print("  TONIGHT'S GAME")
print("="*96)
pend = [r for r in csv.DictReader(open(os.path.join(D, "model_forward.csv"), encoding="utf-8"))
        if not (r.get("result") or "").strip()]
for r in pend:
    pl = (r["player"] or "").lower(); tm = teamof.get(pl)
    if not tm: continue
    want = datetime.datetime.fromisoformat(r["tip"].replace("Z", "+00:00"))
    cands = [g for (t2, g) in oppof if t2 == tm and abs((g - want).total_seconds()) < 7200]
    if not cands: continue
    gt = cands[0]; op = oppof[(tm, gt)]
    a, b = ptsline.get((tm, gt), []), ptsline.get((op, gt), [])
    bt = (sum(a) + sum(b)) if (a and b) else None
    band = "?" if bt is None else ("LOW" if bt <= lo3 else ("HIGH" if bt > hi3 else "MID"))
    print(f"  {r['player']:<18} {r['market'].upper()} {r['line']}  {tm} v {op}")
    print(f"      board-implied total {bt:.1f} ({len(a)}+{len(b)} player lines)  ->  {band} band"
          if bt else "      board total unavailable")
