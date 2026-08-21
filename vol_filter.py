# vol_filter.py - filters ON the volatility gradient: what turns WILD into a bet, what sharpens
# STEADY, and whether any opponent/context flips either.
# ---------------------------------------------------------------------------------------------
# corner_hunt established: wild players' overs -12.0% [CI -17.2,-7.2] vs steady -4.9%, and the
# same gradient inside Model S (+12.4 / +11.2 / +0.1). This asks the follow-up in every direction
# declared up front, one ceiling over the lot:
#   1 WILD x context: is there ANY condition under which a wild player's over pays? (soft/fast
#     opponent, high total, deep cushion, gate-3 star, home) - or her UNDER?
#   2 STEADY x context: does steady + the known good contexts stack into something bettable
#     board-wide (steady + star, steady + deep cushion, steady + soft opponent)?
#   3 the volatility of the OPPONENT's defence: a defence that concedes ERRATICALLY (high sd of
#     what it allows) should be where player lines are least trustworthy - never tested.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260822)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
gof, oppof = {}, {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    gof[(hm, t2)] = gid; gof[(aw, t2)] = gid; oppof[(hm, t2)] = aw; oppof[(aw, t2)] = hm
tg = collections.defaultdict(lambda: collections.defaultdict(float))
for (pl, gt), row in pgrow.items():
    for st in ("pts", "reb", "ast"): tg[(row["tm"], gt)][st] += row[st]
def conc(op, gt):
    a = []
    for t in tips_of.get(op, []):
        if t >= gt: break
        rv = oppof.get((op, t))
        if rv and (rv, t) in tg: a.append(tg[(rv, t)]["pts"])
    if len(a) < 6: return None, None
    a = a[-12:]
    return statistics.mean(a), statistics.pstdev(a)
LGP = {}
def lg_pts(gt):
    if gt in LGP: return LGP[gt]
    v = [x["pts"] for (tm2, t2), x in tg.items() if t2 < gt]
    LGP[gt] = statistics.mean(v) if len(v) >= 40 else None
    return LGP[gt]
def hstat(pl, mk, gt):
    g = [r for r in hist.get(pl, []) if r["tip"] < gt]
    if not g: return None
    cur = g[-1]["tm"]; g2 = [r for r in g if r["tm"] == cur]
    if len(g2) < 6: return None
    v = [r[mk] for r in g2[-10:]]
    return dict(med=statistics.median(v), sd=statistics.pstdev(v))

Q = []
for (pl, mk, gt), sdq in side.items():
    if "Over" not in sdq or "Under" not in sdq: continue
    if abs(sdq["Over"][1] - sdq["Under"][1]) > 0.01: continue
    now = pgrow.get((pl, gt)); tm = teamof.get(pl)
    if not now or mk not in now or not tm: continue
    ln = sdq["Over"][1]
    if now[mk] == ln: continue
    h = hstat(pl, mk, gt)
    if not h or h["sd"] < 0.1: continue
    op = oppof.get((tm, gt))
    cm, cs = conc(op, gt) if op else (None, None)
    lp = lg_pts(gt)
    pv = prevline.get((pl, mk, gt))
    hm_ = gmeta[gof[(tm, gt)]][2] == tm
    Q.append(dict(pl=pl, mk=mk, gt=gt, gid=gof[(tm, gt)], ln=ln,
                  o_od=sdq["Over"][2], u_od=sdq["Under"][2],
                  o_won=now[mk] > ln, u_won=now[mk] < ln,
                  relvol=h["sd"]/max(ln, 1), cush=h["med"]-ln,
                  star=(pv is not None and ln - pv < 0.5),
                  soft=(cm is not None and lp is not None and cm - lp > 1.5),
                  stingy=(cm is not None and lp is not None and cm - lp < -1.5),
                  dvol=(cs if cs is not None else None), home=hm_))
v = sorted(r["relvol"] for r in Q); V1, V2 = v[len(v)//3], v[2*len(v)//3]
for r in Q: r["band"] = "steady" if r["relvol"] <= V1 else ("wild" if r["relvol"] > V2 else "mid")
dv = sorted(r["dvol"] for r in Q if r["dvol"] is not None)
DV = dv[len(dv)//2] if dv else 0
print(f"{len(Q)} quotes; volatility terciles {V1:.3f}/{V2:.3f}; opp-defence-sd median {DV:.1f}")
def ret(r, s): return ((r[s+"_od"]-1) if r[s+"_won"] else -1.0)
def roi(rows, s): return 100*sum(ret(r, s) for r in rows)/len(rows) if rows else 0.0
def hitr(rows, s): return 100*sum(1 for r in rows if r[s+"_won"])/len(rows) if rows else 0.0
def pboot(rows, s, T=2000):
    bp = collections.defaultdict(list)
    for r in rows: bp[r["pl"]].append(r)
    k = list(bp); o = []
    for _ in range(T): o.append(roi([x for p in [random.choice(k) for _ in k] for x in bp[p]], s))
    o.sort(); return o[int(T*.025)], o[int(T*.975)]
CELLS = [
    ("WILD over + SOFT opponent",      lambda r: r["band"] == "wild" and r["soft"], "o"),
    ("WILD over + deep cushion (3+)",  lambda r: r["band"] == "wild" and r["cush"] >= 3, "o"),
    ("WILD over + gate-3 star",        lambda r: r["band"] == "wild" and r["star"], "o"),
    ("WILD over + home",               lambda r: r["band"] == "wild" and r["home"], "o"),
    ("WILD UNDER + STINGY opponent",   lambda r: r["band"] == "wild" and r["stingy"], "u"),
    ("WILD UNDER + line above median", lambda r: r["band"] == "wild" and r["cush"] <= -1, "u"),
    ("WILD UNDER + book raised her",   lambda r: r["band"] == "wild" and not r["star"], "u"),
    ("WILD UNDER + erratic defence",   lambda r: r["band"] == "wild" and r["dvol"] is not None and r["dvol"] > DV, "u"),
    ("STEADY over + star",             lambda r: r["band"] == "steady" and r["star"], "o"),
    ("STEADY over + deep cushion",     lambda r: r["band"] == "steady" and r["cush"] >= 3, "o"),
    ("STEADY over + star + cushion 3+",lambda r: r["band"] == "steady" and r["star"] and r["cush"] >= 3, "o"),
    ("STEADY over + soft opponent",    lambda r: r["band"] == "steady" and r["soft"], "o"),
    ("STEADY over + star + soft opp",  lambda r: r["band"] == "steady" and r["star"] and r["soft"], "o"),
    ("erratic defence, any player: UNDER", lambda r: r["dvol"] is not None and r["dvol"] > DV, "u"),
    ("calm defence, any player: OVER", lambda r: r["dvol"] is not None and r["dvol"] <= DV, "o"),
]
bp = collections.defaultdict(list)
for r in Q: bp[r["pl"]].append(r)
peaks = []
for _ in range(1200):
    pool = [(r["o_won"], r["u_won"]) for r in Q]; random.shuffle(pool)
    for r, x in zip(Q, pool): r["_o"], r["_u"] = x
    best = -99
    for lbl, sel, s in CELLS:
        g = [r for r in Q if sel(r)]
        if len(g) < 60: continue
        wk = "_" + s
        best = max(best, 100*sum((r[s+"_od"]-1) if r[wk] else -1.0 for r in g)/len(g))
    if best > -99: peaks.append(best)
peaks.sort()
CEIL = peaks[int(len(peaks)*0.95)]
print("")
print("="*104)
print(f"  NOISE CEILING FIRST: {len(CELLS)} declared cells -> p95 best {CEIL:+.1f}%  (min n=60)")
print("="*104)
res = []
for lbl, sel, s in CELLS:
    g = [r for r in Q if sel(r)]
    if len(g) < 60:
        print(f"    {lbl:<44} n={len(g)} too few"); continue
    lo, hi = pboot(g, s)
    star = "  <<<" if lo > 0 else ""
    print(f"    {lbl:<44} n={len(g):<5}{hitr(g,s):>6.1f}%{roi(g,s):>+8.1f}%  [{lo:+6.1f},{hi:+6.1f}]{star}")
    res.append((roi(g, s), lbl))
print("")
win = [x for x in res if x[0] > CEIL]
print("  ABOVE THE CEILING: " + (", ".join(f"{l} ({v:+.1f}%)" for v, l in sorted(win, reverse=True)) if win else "none"))
