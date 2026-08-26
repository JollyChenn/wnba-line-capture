# TRACK: first-half carryover. Literal next-game ROI test + mechanism + confound stratification.
import os, sys, csv, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hlib; ROOT = hlib.boot(globals())
random.seed(20260826)
NP = 2000

H1 = {}
for r in load("outputs/hyp/h1_all.csv"):
    gid = r["game_id"]
    if gid not in gmeta: continue
    H1[(r["player"], gmeta[gid][1])] = dict(h1=f(r["h1"]), h2=f(r["h2"]), pts=f(r["pts"]), src=r["src"])
Q = {}
for (pl, mk, gt), sd in side.items():
    if mk != "pts" or "Over" not in sd or "Under" not in sd: continue
    if sd["Over"][1] != sd["Under"][1]: continue
    Q[(pl, gt)] = dict(line=sd["Over"][1], oo=sd["Over"][2], uo=sd["Under"][2])

def prior(pl, gt, k=10):
    return [x for x in hist.get(pl, []) if x["tip"] < gt][-k:]
def med(pl, gt, k=10, mk="pts"):
    p = [x for x in hist.get(pl, []) if x["tip"] < gt]
    p = [x for x in p if x["tm"] == teamof.get(pl)][-k:]   # CURRENT TEAM only (law 7)
    return statistics.median(x[mk] for x in p) if len(p) >= 5 else None

# ---- build pairs -------------------------------------------------------------------
Qg = collections.defaultdict(list)
for (pl, gt) in Q: Qg[pl].append(gt)
for v in Qg.values(): v.sort()
rows = []
for (pl, gt) in sorted(Q, key=lambda k: (k[0], k[1])):
    if (pl, gt) not in H1: continue
    now = pgrow.get((pl, gt))
    if not now or now["min"] < 8: continue
    nxts = [g for g in Qg[pl] if g > gt]
    if not nxts: continue
    n1 = nxts[0]
    nrow = pgrow.get((pl, n1))
    if not nrow or nrow["min"] < 8: continue
    q, qn = Q[(pl, gt)], Q[(pl, n1)]
    m_next = med(pl, n1)
    if m_next is None: continue
    if nrow["pts"] == qn["line"]: continue      # push
    rows.append(dict(pl=pl, gt=gt, n1=n1, line=q["line"], h1=H1[(pl,gt)]["h1"], pts=now["pts"],
                     min=now["min"], nline=qn["line"], noo=qn["oo"], nuo=qn["uo"],
                     npts=nrow["pts"], nmin=nrow["min"], over_won=nrow["pts"] > qn["line"],
                     med_next=m_next, med_g=med(pl, gt), rest=(n1-gt).days,
                     linemv=qn["line"] - q["line"]))
print(f"PAIRS n={len(rows)}  players={len(set(r['pl'] for r in rows))}  G+1 games={len(set(r['n1'] for r in rows))}")
EV = lambda r: r["h1"] > r["line"]
print(f"EVENT (h1 > posted line in G): {sum(1 for r in rows if EV(r))}")

def roi(sel, sd):
    if not sel: return 0.0, 0
    tot = 0.0
    for r in sel:
        if sd == "Over": tot += (r["noo"]-1) if r["over_won"] else -1
        else: tot += (r["nuo"]-1) if not r["over_won"] else -1
    return tot/len(sel), len(sel)

# ---- NOISE CEILING, declared before the table (law 1) -------------------------------
# GRID: 3 event definitions x 2 sides = 6 cells. Null = permute the event label within
# PLAYER blocks (the label is a player-game attribute; players repeat).
DEFS = [("h1>line", lambda r: r["h1"] > r["line"]),
        ("h1>=line", lambda r: r["h1"] >= r["line"]),
        ("h1>=line+2", lambda r: r["h1"] >= r["line"]+2)]
byp = collections.defaultdict(list)
for i, r in enumerate(rows): byp[r["pl"]].append(i)
def best_abs(labels):
    b = 0.0
    for _, fn in DEFS:
        sel = [rows[i] for i in range(len(rows)) if labels[i]]
        pass
    return b
def grid_best(flagmap):
    b = 0.0; who = None
    for nm, _ in DEFS:
        sel = [r for r in rows if flagmap[nm][id(r)]]
        if len(sel) < 20: continue
        for sd in ("Over","Under"):
            v, n = roi(sel, sd)
            if abs(v) > abs(b): b, who = v, (nm, sd, n)
    return b, who
real_flags = {nm: {id(r): fn(r) for r in rows} for nm, fn in DEFS}
null = []
for _ in range(NP):
    fm = {nm: {} for nm, _ in DEFS}
    for pl, idx in byp.items():
        for nm, _ in DEFS:
            vals = [real_flags[nm][id(rows[i])] for i in idx]
            random.shuffle(vals)
            for i, v in zip(idx, vals): fm[nm][id(rows[i])] = v
    b, _ = grid_best(fm)
    null.append(abs(b))
null.sort()
CEIL = null[int(0.95*len(null))]
print(f"\nNOISE CEILING (player-block permutation, {NP} draws, grid = 3 event defs x 2 sides):")
print(f"  p95 of best |ROI| in the grid under the null = {CEIL:+.2%}   (median {null[len(null)//2]:+.2%})")

print("\n%-12s %-6s %5s %5s %8s %8s" % ("event", "side", "n", "plyr", "ROI", "hit%"))
for nm, fn in DEFS:
    sel = [r for r in rows if fn(r)]
    npl = len(set(r["pl"] for r in sel))
    for sd in ("Over","Under"):
        v, n = roi(sel, sd)
        hit = sum(1 for r in sel if (r["over_won"] if sd=="Over" else not r["over_won"]))/max(1,len(sel))
        print("%-12s %-6s %5d %5d %+8.2f%% %7.1f%%  %s" % (nm, sd, n, npl, 100*v, 100*hit, "CLEARS" if abs(v)>CEIL else "under ceiling"))
    csel = [r for r in rows if not fn(r)]
    for sd in ("Over","Under"):
        v, n = roi(csel, sd)
        print("  %-10s %-6s %5d %5s %+8.2f%%  (control: NOT event)" % ("~"+nm, sd, n, "", 100*v))

# block bootstrap CI on the primary cell
def boot_ci(sel_pred, sd, B=4000):
    pls = sorted(set(r["pl"] for r in rows))
    bypl = {p: [r for r in rows if r["pl"] == p] for p in pls}
    out = []
    for _ in range(B):
        s = []
        for _ in range(len(pls)):
            s += bypl[random.choice(pls)]
        s = [r for r in s if sel_pred(r)]
        if len(s) < 5: continue
        out.append(roi(s, sd)[0])
    out.sort()
    return out[int(.025*len(out))], out[int(.975*len(out))]
lo, hi = boot_ci(EV, "Over")
print(f"\nPRIMARY  event=h1>line, side=Over : block-bootstrap 95% CI [{lo:+.1%}, {hi:+.1%}]")
lo2, hi2 = boot_ci(EV, "Under")
print(f"PRIMARY  event=h1>line, side=Under: block-bootstrap 95% CI [{lo2:+.1%}, {hi2:+.1%}]")
import pickle
pickle.dump(rows, open(os.path.join(ROOT,"outputs","hyp","h1_pairs.pkl"),"wb"))
