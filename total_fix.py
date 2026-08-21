# total_fix.py - my board-implied total was confounded by coverage. Does the finding survive?
# ---------------------------------------------------------------------------------------------
# btot = sum of every posted points line in the game. That is not a total, it is a total MIXED
# WITH how many players the book bothered to quote. Tonight's LV v CON shows it: 86.5 from seven
# lines against 137.0 from ten, which reads as a slow game but is really a thin one. Per posted
# line the two are 12.4 and 13.7 - barely different.
#
# So the "LOW total games cost overs 10%" result may be measuring the wrong thing entirely. Three
# repairs, and the finding has to survive all three to be believed:
#   COUNT-MATCHED   only games with 9+ posted lines, so coverage is roughly constant
#   PER-LINE        mean posted line instead of the sum - immune to how many were posted
#   REALISED        the actual final score, which is what "low scoring" really means and needs no
#                   proxy at all. If the effect is real it should be clearest here.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260820)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
ALLMK = ("pts", "pr", "pra", "pa", "ra", "reb", "ast")
gof, oppof = {}, {}
realtot = {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    gof[(hm, t2)] = gid; gof[(aw, t2)] = gid
    oppof[(hm, t2)] = aw; oppof[(aw, t2)] = hm
for g in load("data/games_2026.csv"):
    a_, h_ = f(g.get("away_score")), f(g.get("home_score"))
    if a_ is not None and h_ is not None: realtot[g.get("game_id")] = a_ + h_
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
    op = oppof.get((tm, gt))
    a, b = ptsline.get((tm, gt), []), ptsline.get((op, gt), [])
    nlines = len(a) + len(b)
    if nlines < 4: continue
    gid = gof[(tm, gt)]
    md = med_team(pl, mk, gt)
    Q.append(dict(pl=pl, mk=mk, gid=gid, tm=tm, mkt=mk, nlines=nlines,
                  btot=sum(a)+sum(b), perline=(sum(a)+sum(b))/nlines,
                  real=realtot.get(gid),
                  o_od=sdq["Over"][2], o_won=now[mk] > ln,
                  cush=(md - ln) if md is not None else None))
def roi(rows): return 100*sum((r["o_od"]-1) if r["o_won"] else -1.0 for r in rows)/len(rows) if rows else 0
def hit(rows): return 100*sum(1 for r in rows if r["o_won"])/len(rows) if rows else 0
def gboot(rows, T=2000):
    bg = collections.defaultdict(list)
    for r in rows: bg[r["gid"]].append(r)
    k = list(bg); o = []
    for _ in range(T): o.append(roi([x for p in [random.choice(k) for _ in k] for x in bg[p]]))
    o.sort(); return o[int(T*.025)], o[int(T*.975)]
def terc(rows, key, lbl, minn=200):
    v = sorted(r[key] for r in rows if r.get(key) is not None)
    if len(v) < 3*minn: print(f"  {lbl}: n={len(v)} too few"); return
    a, b = v[len(v)//3], v[2*len(v)//3]
    print(f"  {lbl}   terciles {a:.1f} / {b:.1f}")
    for nm, sel in ((" LOW ", lambda r: r[key] <= a), (" MID ", lambda r: a < r[key] <= b),
                    (" HIGH", lambda r: r[key] > b)):
        g = [r for r in rows if r.get(key) is not None and sel(r)]
        lo, hi = gboot(g)
        print(f"     {nm}  n={len(g):<5}{hit(g):>6.1f}%{roi(g):>+8.1f}%  95CI [{lo:+6.1f},{hi:+6.1f}]")
    print("")

print(f"{len(Q)} overs; posted-line counts: " +
      ", ".join(f"{k}:{v}" for k, v in sorted(collections.Counter(r['nlines'] for r in Q).items())[:12]))
print("")
print("="*96)
print("  IS 'LOW TOTAL' JUST 'FEW LINES POSTED'?")
print("="*96)
cc = collections.defaultdict(list)
for r in Q: cc[r["nlines"]].append(r["btot"])
print("  mean btot by number of posted lines:")
for k in sorted(cc):
    if len(cc[k]) < 40: continue
    print(f"    {k:>3} lines  ->  btot {statistics.mean(cc[k]):6.1f}   (n={len(cc[k])})")
print("")
print("  they move together almost perfectly, which is the confound.")
print("")
print("="*96)
print("  THE THREE REPAIRS")
print("="*96)
terc(Q, "btot", "1. RAW SUM (what I reported - confounded)")
terc([r for r in Q if r["nlines"] >= 9], "btot", "2. COUNT-MATCHED (9+ posted lines only)", minn=120)
terc(Q, "perline", "3. PER-LINE mean (immune to coverage)")
terc([r for r in Q if r["real"] is not None], "real", "4. REALISED final score (no proxy at all)")
print("="*96)
print("  AND THE DEEP-CUSHION INTERACTION, on the realised score")
print("="*96)
DP = [r for r in Q if r["cush"] is not None and r["cush"] >= 3 and r["real"] is not None]
v = sorted(r["real"] for r in DP)
if len(v) >= 90:
    a, b = v[len(v)//3], v[2*len(v)//3]
    for nm, sel in ((f"cushion 3+, LOW-scoring game (<= {a:.0f})", lambda r: r["real"] <= a),
                    (f"cushion 3+, MID", lambda r: a < r["real"] <= b),
                    (f"cushion 3+, HIGH-scoring game (> {b:.0f})", lambda r: r["real"] > b)):
        g = [r for r in DP if sel(r)]
        print(f"  {nm:<44} n={len(g):<5}{hit(g):>6.1f}%{roi(g):>+8.1f}%")
print("")
print("  NOTE: the realised score is NOT knowable before tip. It is here only to establish whether")
print("  the pace effect is real at all. If it is, the board-implied version is worth repairing;")
print("  if even the realised score shows nothing, the whole line of enquiry is dead.")
