import os, sys, csv, math, random, statistics, datetime, collections, pickle
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hlib; ROOT = hlib.boot(globals())
random.seed(20260826)

H1 = {}
for r in load("outputs/hyp/h1_all.csv"):
    gid = r["game_id"]
    if gid not in gmeta: continue
    H1[(r["player"], gmeta[gid][1])] = dict(h1=f(r["h1"]), h2=f(r["h2"]), pts=f(r["pts"]), src=r["src"])

# ---------------- Q5: H1/H2 split distribution -------------------------------------
print("="*78); print("Q5  H1 / H2 SCORING SPLIT - a durable fact")
tot_h1 = sum(v["h1"] for v in H1.values()); tot_p = sum(v["pts"] for v in H1.values())
print("  league-wide H1 share of points: %.4f  (n=%d player-games, %d games)" %
      (tot_h1/tot_p, len(H1), len(set(gt for _, gt in H1))))
sh = sorted(v["h1"]/v["pts"] for v in H1.values() if v["pts"] >= 8)
print("  per player-game share (pts>=8, n=%d): mean %.3f sd %.3f  p10 %.3f p25 %.3f med %.3f p75 %.3f p90 %.3f" %
      (len(sh), statistics.mean(sh), statistics.pstdev(sh), sh[int(.1*len(sh))], sh[int(.25*len(sh))],
       sh[len(sh)//2], sh[int(.75*len(sh))], sh[int(.9*len(sh))]))
byp = collections.defaultdict(list)
for (pl, gt), v in H1.items():
    if v["pts"] >= 8: byp[pl].append(v["h1"]/v["pts"])
reg = {p: v for p, v in byp.items() if len(v) >= 8}
pm = [statistics.mean(v) for v in reg.values()]
print("  player mean share (>=8 qualifying games, %d players): mean %.3f sd %.3f  min %.3f max %.3f" %
      (len(reg), statistics.mean(pm), statistics.pstdev(pm), min(pm), max(pm)))
wi = statistics.mean(statistics.pvariance(v) for v in reg.values())
bw = statistics.pvariance(pm)
print("  variance decomposition: between-player %.5f | within-player %.5f | ICC %.3f" % (bw, wi, bw/(bw+wi)))
rs = []
for p, v in reg.items():
    a = v[0::2]; b = v[1::2]
    if len(a) >= 3 and len(b) >= 3: rs.append((statistics.mean(a), statistics.mean(b)))
mx = statistics.mean(x for x, _ in rs); my = statistics.mean(y for _, y in rs)
num = sum((x-mx)*(y-my) for x, y in rs)
den = math.sqrt(sum((x-mx)**2 for x, _ in rs)*sum((y-my)**2 for _, y in rs))
rr = num/den
print("  odd/even split-half correlation of a player H1 share: r = %+.3f (n=%d players) -> %s" %
      (rr, len(rs), "no stable player-level H1-share skill" if abs(rr) < 0.25 else "some stability"))

# ---------------- Q4a: same-game other markets --------------------------------------
print("")
print("="*78); print("Q4a SAME-GAME: given she cleared PTS by halftime, do her PR / PRA overs land?")
pre = 0; post = 0
for b in load("xbet_board.csv"):
    t = ts(b.get("captured_utc"))
    if not t: continue
    tm2 = teamof.get(_pl(b.get("player")))
    g2 = game_for(tm2, t) if tm2 else None
    if g2: pre += 1
    else: post += 1
print("  EXECUTABILITY: %d board quotes map to a forward game, %d do not." % (pre, post))
print("  There is NO halftime price anywhere in this repo, so the result below is DIAGNOSTIC ONLY:")
print("  pricing a pre-game line with halftime knowledge is look-ahead (law 5 / law 7).")
S2 = {}
for (pl, mk, gt), sd in side.items():
    if mk in ("pr", "pra", "ra") and "Over" in sd and "Under" in sd and sd["Over"][1] == sd["Under"][1]:
        S2[(pl, mk, gt)] = (sd["Over"][1], sd["Over"][2], sd["Under"][2])
P1 = {}
for (pl, mk, gt), sd in side.items():
    if mk == "pts" and "Over" in sd and "Under" in sd and sd["Over"][1] == sd["Under"][1]:
        P1[(pl, gt)] = sd["Over"][1]
print("")
print("%-5s %6s %9s %9s %11s %12s" % ("mkt", "n", "evOver%", "noOver%", "gap", "diagROI(Ov)"))
for mk in ("pr", "pra"):
    rows = []
    for (pl, m2, gt), (ln, oo, uo) in S2.items():
        if m2 != mk: continue
        if (pl, gt) not in P1 or (pl, gt) not in H1: continue
        nowr = pgrow.get((pl, gt))
        if not nowr or nowr["min"] < 8 or nowr[mk] == ln: continue
        rows.append((H1[(pl, gt)]["h1"] > P1[(pl, gt)], nowr[mk] > ln, oo, uo))
    a = [r for r in rows if r[0]]; b = [r for r in rows if not r[0]]
    if len(a) < 5:
        print("%-5s %6d  (too few events: %d)" % (mk, len(rows), len(a))); continue
    ao = sum(1 for r in a if r[1])/len(a); bo = sum(1 for r in b if r[1])/len(b)
    ro = sum((r[2]-1) if r[1] else -1 for r in a)/len(a)
    print("%-5s %6d %8.1f%% %8.1f%% %+10.1fpp %+11.2f%%  (nEv=%d)" %
          (mk, len(rows), 100*ao, 100*bo, 100*(ao-bo), 100*ro, len(a)))

# ---------------- Q4b: does the book OVER-adjust her next line? ----------------------
print("")
print("="*78); print("Q4b BOOK OVERREACTION: does the next line move MORE than production justifies?")
Qg = collections.defaultdict(list)
for (pl, gt) in P1: Qg[pl].append(gt)
for v in Qg.values(): v.sort()
def trail(pl, gt, k=10):
    p = [x for x in hist.get(pl, []) if x["tip"] < gt and x["tm"] == teamof.get(pl)][-k:]
    return statistics.median(x["pts"] for x in p) if len(p) >= 5 else None
pairs = []
for (pl, gt), ln in P1.items():
    if (pl, gt) not in H1: continue
    nowr = pgrow.get((pl, gt))
    if not nowr or nowr["min"] < 8: continue
    nx = [g for g in Qg[pl] if g > gt]
    if not nx: continue
    n1 = nx[0]; nrow = pgrow.get((pl, n1))
    if not nrow or nrow["min"] < 8: continue
    mg = trail(pl, gt)
    if mg is None or nrow["pts"] == P1[(pl, n1)]: continue
    pairs.append(dict(pl=pl, gt=gt, n1=n1, line=ln, nline=P1[(pl, n1)], mv=P1[(pl, n1)]-ln,
                      h1=H1[(pl, gt)]["h1"], pts=nowr["pts"], med=mg, resid_g=nowr["pts"]-mg,
                      npts=nrow["pts"], nresid=nrow["pts"]-mg,
                      over_won=nrow["pts"] > P1[(pl, n1)],
                      noo=side[(pl, "pts", n1)]["Over"][2], nuo=side[(pl, "pts", n1)]["Under"][2],
                      ev=H1[(pl, gt)]["h1"] > ln))
print("  pairs n=%d  players=%d  events=%d" % (len(pairs), len(set(p["pl"] for p in pairs)),
                                               sum(1 for p in pairs if p["ev"])))
ev = [p for p in pairs if p["ev"]]; ne = [p for p in pairs if not p["ev"]]
print("  mean line move G->G+1:  event %+.3f pts (n=%d) | non-event %+.3f (n=%d)" %
      (statistics.mean(p["mv"] for p in ev), len(ev), statistics.mean(p["mv"] for p in ne), len(ne)))
print("  mean resid_g:           event %+.2f | non-event %+.2f" %
      (statistics.mean(p["resid_g"] for p in ev), statistics.mean(p["resid_g"] for p in ne)))
print("  mean NEXT-game resid:   event %+.2f | non-event %+.2f" %
      (statistics.mean(p["nresid"] for p in ev), statistics.mean(p["nresid"] for p in ne)))
me = statistics.mean(p["mv"] for p in ev); re_ = statistics.mean(p["resid_g"] for p in ev)
nr = statistics.mean(p["nresid"] for p in ev)
print("  -> after an event the book moved %+.3f pts; she then delivered %+.2f over the OLD median." % (me, nr))
print("     line captured %.0f%% of the production she actually repeated." % (100*me/max(.01, nr)))

def ols(X, y):
    k = len(X[0])
    A = [[sum(X[i][a]*X[i][b] for i in range(len(X))) for b in range(k)] for a in range(k)]
    Bv = [sum(X[i][a]*y[i] for i in range(len(X))) for a in range(k)]
    Aa = [row[:]+[Bv[i]] for i, row in enumerate(A)]
    for c in range(k):
        p = max(range(c, k), key=lambda r_: abs(Aa[r_][c])); Aa[c], Aa[p] = Aa[p], Aa[c]
        for r_ in range(k):
            if r_ == c or Aa[c][c] == 0: continue
            fq = Aa[r_][c]/Aa[c][c]
            for cc in range(c, k+1): Aa[r_][cc] -= fq*Aa[c][cc]
    return [Aa[i][k]/Aa[i][i] for i in range(k)]

X = [(1.0, p["resid_g"], p["h1"] - p["line"]) for p in pairs]
y = [p["mv"] for p in pairs]
bt = ols(X, y)
print("")
print("  line_move ~ a + b*resid_g + c*(h1 - line_G):   a %+.3f  b %+.4f  c %+.4f" % tuple(bt))
byp2 = collections.defaultdict(list)
for i, p in enumerate(pairs): byp2[p["pl"]].append(i)
cnt = 0; B = 3000
for _ in range(B):
    col = [X[i][2] for i in range(len(X))]
    for p_, ii in byp2.items():
        v = [col[i] for i in ii]; random.shuffle(v)
        for i, x in zip(ii, v): col[i] = x
    try:
        if abs(ols([(1.0, X[i][1], col[i]) for i in range(len(X))], y)[2]) >= abs(bt[2]): cnt += 1
    except ZeroDivisionError: pass
print("  player-block permutation p on c (H1 extra pull on the line) = %.4f" % ((cnt+1)/(B+1)))
print("")
print("  ROI at G+1 by line-move bucket, EVENT rows only (n=%d):" % len(ev))
for lo, hi, nm in [(-99, 0.001, "not raised"), (0.001, 1.501, "raised <=1.5"), (1.501, 99, "raised >1.5")]:
    s = [p for p in ev if lo <= p["mv"] < hi]
    if len(s) < 5:
        print("    %-14s n=%d (too few)" % (nm, len(s))); continue
    ro = sum((p["noo"]-1) if p["over_won"] else -1 for p in s)/len(s)
    ru = sum((p["nuo"]-1) if not p["over_won"] else -1 for p in s)/len(s)
    print("    %-14s n=%3d  players=%2d  Over %+7.2f%%  Under %+7.2f%%" %
          (nm, len(s), len(set(p["pl"] for p in s)), 100*ro, 100*ru))
print("")
print("  same buckets on ALL pairs (event and not), for the ceiling comparison:")
for lo, hi, nm in [(-99, 0.001, "not raised"), (0.001, 1.501, "raised <=1.5"), (1.501, 99, "raised >1.5")]:
    s = [p for p in pairs if lo <= p["mv"] < hi]
    if len(s) < 5: continue
    ro = sum((p["noo"]-1) if p["over_won"] else -1 for p in s)/len(s)
    ru = sum((p["nuo"]-1) if not p["over_won"] else -1 for p in s)/len(s)
    print("    %-14s n=%3d  players=%2d  Over %+7.2f%%  Under %+7.2f%%" %
          (nm, len(s), len(set(p["pl"] for p in s)), 100*ro, 100*ru))
