# CONFOUND LENS on the "first-half carryover" mechanism claim.
# Claim: h1 > reference line in G  ->  next game pts is +1.49 above her trailing median
#        vs non-events (n=1969, player-block p=0.0045).
# Suspected confounds:
#   C1 SHARED BASELINE  med_G is used BOTH inside the event label (ref) AND as the subtraction
#      in the outcome (resid = npts - med_G).  Noise/bias in med_G couples label to outcome.
#   C2 BIG-GAME / VOLUME PROXY  h1>ref is a noisy indicator of "she had a big game in G".
#   C3 ALWAYS-POSITIVE BASE RATE  both arms are positive (median < mean for right-skew pts).
import os, sys, csv, math, random, statistics, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hlib; ROOT = hlib.boot(globals())
random.seed(20260826)

H1 = {}
for r in load("outputs/hyp/h1_all.csv"):
    gid = r["game_id"]
    if gid not in gmeta: continue
    H1[(r["player"], gmeta[gid][1])] = dict(h1=f(r["h1"]), pts=f(r["pts"]))
Q = {}
for (pl, mk, gt), sd in side.items():
    if mk != "pts" or "Over" not in sd or "Under" not in sd: continue
    if sd["Over"][1] != sd["Under"][1]: continue
    Q[(pl, gt)] = sd["Over"][1]

def prior(pl, gt, k=10):
    return [x for x in hist.get(pl, []) if x["tip"] < gt and x["tm"] == teamof.get(pl)][-k:]

M = []
for (pl, gt), h in sorted(H1.items()):
    now = pgrow.get((pl, gt))
    if not now or now["min"] < 8: continue
    p = prior(pl, gt)
    if len(p) < 5: continue
    m_g = statistics.median(x["pts"] for x in p)
    A = [x["pts"] for x in p[0::2]]; Bp = [x["pts"] for x in p[1::2]]
    if len(A) < 2 or len(Bp) < 2: continue
    medA, medB = statistics.median(A), statistics.median(Bp)
    fut = [x for x in hist.get(pl, []) if x["tip"] > gt]
    if not fut: continue
    nx = fut[0]
    if nx["min"] < 8: continue
    line = Q.get((pl, gt)); ref = line if line is not None else m_g
    M.append(dict(pl=pl, gt=gt, h1=h["h1"], pts=now["pts"], mn=now["min"],
                  ref=ref, med=m_g, medA=medA, medB=medB, real=(line is not None),
                  npts=nx["pts"], nmin=nx["min"],
                  resid=nx["pts"]-m_g, resid_g=now["pts"]-m_g))
EV = lambda r: r["h1"] > r["ref"]
ev = [r for r in M if EV(r)]; ne = [r for r in M if not EV(r)]
print("panel n=%d  players=%d  events=%d" % (len(M), len(set(r['pl'] for r in M)), len(ev)))
obs = statistics.mean(r["resid"] for r in ev) - statistics.mean(r["resid"] for r in ne)
print("REPLICATION of headline gap: %+.3f pts (ev %+.2f n=%d | non %+.2f n=%d)" % (
      obs, statistics.mean(r["resid"] for r in ev), len(ev),
      statistics.mean(r["resid"] for r in ne), len(ne)))
print("")

print("--- C3  ALWAYS-POSITIVE BASE RATE ---")
allr = [r["resid"] for r in M]
print("  every-row mean resid %+.3f (median %+.2f); share resid>0 = %.1f%%" % (
      statistics.mean(allr), statistics.median(allr), 100*sum(1 for x in allr if x > 0)/len(allr)))
print("")

print("--- C1  SHARED-BASELINE IMBALANCE (med_G sits on BOTH sides of the test) ---")
dm = statistics.mean(r["med"] for r in ev) - statistics.mean(r["med"] for r in ne)
dn = statistics.mean(r["npts"] for r in ev) - statistics.mean(r["npts"] for r in ne)
print("  mean med_G  event %.2f vs non %.2f  -> delta %+.3f" % (
      statistics.mean(r["med"] for r in ev), statistics.mean(r["med"] for r in ne), dm))
print("  mean npts   event %.2f vs non %.2f  -> delta %+.3f" % (
      statistics.mean(r["npts"] for r in ev), statistics.mean(r["npts"] for r in ne), dn))
print("  identity: gap %+.3f = delta_npts %+.3f - delta_med %+.3f" % (obs, dn, dm))
byp = collections.defaultdict(list)
for i, r in enumerate(M): byp[r["pl"]].append(i)
wm = {}
for p_, ii in byp.items():
    wm[p_] = (statistics.mean(M[i]["med"] for i in ii), statistics.mean(M[i]["npts"] for i in ii))
dmw = statistics.mean(r["med"]-wm[r["pl"]][0] for r in ev) - statistics.mean(r["med"]-wm[r["pl"]][0] for r in ne)
dnw = statistics.mean(r["npts"]-wm[r["pl"]][1] for r in ev) - statistics.mean(r["npts"]-wm[r["pl"]][1] for r in ne)
print("  WITHIN-PLAYER (what the block permutation sees):")
print("    delta_med %+.3f  delta_npts %+.3f  -> baseline term is %.0f%% of the within-player gap" % (
      dmw, dnw, 100*(-dmw)/max(1e-9, (dnw-dmw))))
print("")

print("--- C1b SYNTHETIC NULL (noise ceiling): resample next-game pts i.i.d. from each player's")
print("        own season pool. Carryover destroyed; med_G coupling kept. ---")
pool = {p_: [x["pts"] for x in hist.get(p_, [])] for p_ in byp}
sims = []
for _ in range(2000):
    a = []; b = []
    for r in M:
        v = random.choice(pool[r["pl"]]) - r["med"]
        (a if EV(r) else b).append(v)
    sims.append(statistics.mean(a) - statistics.mean(b))
sims.sort()
print("  null gap: mean %+.3f  p50 %+.3f  p95 %+.3f  p99 %+.3f" % (
      statistics.mean(sims), sims[1000], sims[int(.95*2000)], sims[int(.99*2000)]))
print("  observed %+.3f -> %s the pure-artifact null; artifact share %.0f%%" % (
      obs, "ABOVE" if obs > sims[int(.95*2000)] else "INSIDE", 100*statistics.mean(sims)/obs))
print("")

def blockp(rows, labfn, valfn, B=4000):
    a = [valfn(r) for r in rows if labfn(r)]; b = [valfn(r) for r in rows if not labfn(r)]
    if len(a) < 5 or len(b) < 5: return None, None, len(a), len(b)
    o = statistics.mean(a) - statistics.mean(b)
    bb = collections.defaultdict(list)
    for i, r in enumerate(rows): bb[r["pl"]].append(i)
    lab = [labfn(r) for r in rows]; c = 0
    for _ in range(B):
        l2 = list(lab)
        for _p, ii in bb.items():
            v = [lab[i] for i in ii]; random.shuffle(v)
            for i, x in zip(ii, v): l2[i] = x
        aa = [valfn(rows[i]) for i in range(len(rows)) if l2[i]]
        bv = [valfn(rows[i]) for i in range(len(rows)) if not l2[i]]
        if len(aa) >= 5 and len(bv) >= 5 and abs(statistics.mean(aa)-statistics.mean(bv)) >= abs(o): c += 1
    return o, (c+1)/(B+1), len(a), len(b)

print("--- C1c DISJOINT-BASELINE REBUILD (label uses one half of the trailing window,")
print("        outcome baseline the other half: same window, independent noise) ---")
for nm, lab, val in [
    ("SAME baseline  (h1>medA | npts-medA)", lambda r: r["h1"] > r["medA"], lambda r: r["npts"]-r["medA"]),
    ("DISJOINT       (h1>medA | npts-medB)", lambda r: r["h1"] > r["medA"], lambda r: r["npts"]-r["medB"]),
    ("DISJOINT flip  (h1>medB | npts-medA)", lambda r: r["h1"] > r["medB"], lambda r: r["npts"]-r["medA"]),
]:
    o, p, na, nb = blockp(M, lab, val)
    print("  %-38s gap %+6.3f  p=%.4f  (nEv %d / nNon %d)" % (nm, o, p, na, nb))
print("")

print("--- C2 ROLE + BIG-GAME PROXY ---")
print("  mean min_G ev %.1f vs non %.1f ; mean pts_G ev %.1f vs non %.1f" % (
      statistics.mean(r["mn"] for r in ev), statistics.mean(r["mn"] for r in ne),
      statistics.mean(r["pts"] for r in ev), statistics.mean(r["pts"] for r in ne)))
o, p, na, nb = blockp(M, lambda r: r["pts"] > r["ref"], lambda r: r["resid"])
print("  CONTROL 'full-game pts_G > ref' (zero half information): gap %+.3f p=%.4f n=%d/%d" % (o, p, na, nb))
o2, p2, na2, nb2 = blockp(M, lambda r: r["mn"] >= 30, lambda r: r["resid"])
print("  CONTROL 'min_G >= 30' (pure volume, no scoring info):    gap %+.3f p=%.4f n=%d/%d" % (o2, p2, na2, nb2))
o3, p3, na3, nb3 = blockp([r for r in M if r["pts"] > r["ref"]], EV, lambda r: r["resid"])
print("  H1 label INSIDE the 'cleared full-game line' subset:     gap %+.3f p=%.4f n=%d/%d" % (o3, p3, na3, nb3))
print("")

print("--- CONTROLLED REBUILD: same player, matched pts_G and min_G, disjoint baseline ---")
nebyp = collections.defaultdict(list)
for r in M:
    if not EV(r): nebyp[r["pl"]].append(r)
d = []
for r in M:
    if not EV(r): continue
    c = [q for q in nebyp[r["pl"]] if abs(q["pts"]-r["pts"]) <= 1 and abs(q["mn"]-r["mn"]) <= 6]
    if not c: continue
    d.append((r["npts"]-r["medB"]) - statistics.mean(q["npts"]-q["medB"] for q in c))
if d:
    se = statistics.pstdev(d)/math.sqrt(len(d))
    m = statistics.mean(d)
    print("  n=%d pairs  mean(event - control) %+.3f pts  se %.3f  t %+.2f  95%%CI [%+.2f,%+.2f]" % (
          len(d), m, se, m/se, m-1.96*se, m+1.96*se))
