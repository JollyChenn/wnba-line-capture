# fam_final.py - final robustness pass on the one cell that survived the sub-grid table:
#   "newunder FADE | notCUT"  (bet the OVER against the ftunder family when the book has
#   NOT cut her line vs her previous game).
# Checks: size-matched ceiling, within-family contrast null, PLAYER-block null (the label
# clusters on players), price-timing sensitivity, market breakdown, and the mechanism
# contradiction against the board-wide line-move gradient.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])

def nd(s): return (s or "").replace("-", "")[:8]
G = load("graded_bets.csv"); L = load("bets_log.csv")
li = collections.defaultdict(list)
for r in L:
    t = ts(r["captured_utc"])
    if t: li[(nd(r["date"]), (r["player"] or "").lower(), r["market"], r["side"])].append((t, r))
for v in li.values(): v.sort(key=lambda z: z[0])
bi = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None:
        bi[((b.get("player") or "").lower(), b.get("market"), b.get("side"), ln)].append((t, o))
dt2tip = collections.defaultdict(list)
for (pl, tp), row in pgrow.items(): dt2tip[(pl, row["date"])].append(tp)

BETS = []
for r in G:
    pl = (r["player"] or "").lower(); d = nd(r["date"]); mk = r["market"]; sd = r["side"]
    ln = f(r["line"]); od = f(r["odds"]); act = f(r["actual"])
    if ln is None or od is None or act is None: continue
    tps = dt2tip.get((pl, d))
    if not tps: continue
    gt = tps[0]
    if act == ln: continue
    rows = li.get((d, pl, mk, sd), []); ex = [z for z in rows if f(z[1]["line"]) == ln]
    sr = ex or rows
    T = sr[0][0] if sr else gt - datetime.timedelta(hours=12)
    opp = "Under" if sd == "Over" else "Over"
    cand = [z for z in bi.get((pl, mk, opp, ln), []) if z[0] <= gt and (gt - z[0]).total_seconds() <= 60 * 3600]
    oppod = min(cand, key=lambda z: abs((z[0] - T).total_seconds()))[1] if cand else None
    opplast = max(cand, key=lambda z: z[0])[1] if cand else None   # timing sensitivity
    oppworst = min(z[1] for z in cand) if cand else None           # worst price we could have got
    prev = prevline.get((pl, mk, gt))
    over_won = act > ln
    BETS.append(dict(date=d, pl=pl, mk=mk, sd=sd, ln=ln, od=od, oppod=oppod, opplast=opplast,
                     oppworst=oppworst, gt=gt, act=act, over_won=over_won,
                     won=(over_won if sd == "Over" else (not over_won)),
                     src=r["src"], mv=(None if prev is None else ln - prev)))
NU = [b for b in BETS if b["src"] == "newunder" and b["oppod"] is not None and b["mv"] is not None]
NOTCUT = [b for b in NU if b["mv"] > -0.5]
CUT = [b for b in NU if b["mv"] <= -0.5]
def froi(rows, key="oppod"):
    return sum((b[key] - 1) if not b["won"] else -1.0 for b in rows) / len(rows)
def eroi(rows):
    return sum((b["od"] - 1) if b["won"] else -1.0 for b in rows) / len(rows)

print("=" * 100)
print("  A. THE CELL")
print("=" * 100)
print("  newunder, two-sided, line-move known: n=%d   notCUT n=%d   CUT n=%d" % (len(NU), len(NOTCUT), len(CUT)))
print("  notCUT  EMIT %+6.1f%%   FADE %+6.1f%%   over-rate %.1f%%"
      % (100 * eroi(NOTCUT), 100 * froi(NOTCUT), 100 * sum(1 for b in NOTCUT if b["over_won"]) / len(NOTCUT)))
print("  CUT     EMIT %+6.1f%%   FADE %+6.1f%%   over-rate %.1f%%"
      % (100 * eroi(CUT), 100 * froi(CUT), 100 * sum(1 for b in CUT if b["over_won"]) / len(CUT)))

print("\n  price-timing sensitivity on the FADE (law 5 - same-instant vs other choices):")
for k, lbl in (("oppod", "nearest to ping time  "), ("opplast", "last quote before tip "),
               ("oppworst", "worst quote in window ")):
    g = [b for b in NOTCUT if b[k] is not None]
    print("    %s n=%d  FADE %+6.1f%%  (median price %.3f)"
          % (lbl, len(g), 100 * froi(g, k), statistics.median([b[k] for b in g])))

print("\n" + "=" * 100)
print("  B. SIZE-MATCHED CEILING (secondary, post-hoc stratification - stated as such)")
print("=" * 100)
FAM4 = ("newunder", "overshoot", "flip_paper", "cascade")
BUCK = (("ALL", lambda b: True), ("CUT<=-.5", lambda b: b["mv"] <= -0.5),
        ("FLAT", lambda b: -0.5 < b["mv"] < 0.5), ("RAISED>=.5", lambda b: b["mv"] >= 0.5),
        ("notCUT", lambda b: b["mv"] > -0.5), ("notRAISED", lambda b: b["mv"] < 0.5))
TWO = [b for b in BETS if b["oppod"] is not None and b["mv"] is not None]
def cells(minn):
    out = []
    for fam in FAM4:
        for dirn in ("EMIT", "FADE"):
            for bn, bf in BUCK:
                rows = [b for b in TWO if b["src"] == fam and bf(b)]
                if len(rows) >= minn: out.append(("%s %s | %s" % (fam, dirn, bn), rows, dirn))
    return out
def roi(rows, dirn, lab):
    p = 0.0
    for b in rows:
        w = lab[id(b)]
        p += ((b["od"] - 1) if w else -1.0) if dirn == "EMIT" else (-1.0 if w else (b["oppod"] - 1))
    return p / len(rows)
gb = collections.defaultdict(list)
for b in TWO: gb[b["gt"]].append(b)
gblocks = [v for k, v in sorted(gb.items())]
gflat = [b for blk in gblocks for b in blk]
pb = collections.defaultdict(list)
for b in TWO: pb[b["pl"]].append(b)
pblocks = [v for k, v in sorted(pb.items())]
pflat = [b for blk in pblocks for b in blk]
def perm(blocks, flat):
    bl = list(blocks); random.shuffle(bl)
    stream = [b["won"] for blk in bl for b in blk]
    return {id(b): w for b, w in zip(flat, stream)}
real = {id(b): b["won"] for b in TWO}
T = 3000
for minn, lbl in ((60, "primary  n>=60 "), (150, "size-matched n>=150")):
    lv = cells(minn)
    sims = sorted(max(roi(r, d, perm(gblocks, gflat)) for nm, r, d in lv) for _ in range(T))
    print("  %s  %d cells  ceiling p95 %+.1f%%   (best real cell %+.1f%% = %s)"
          % (lbl, len(lv), 100 * sims[int(T * 0.95)],
             100 * max(roi(r, d, real) for nm, r, d in lv),
             max(((roi(r, d, real), nm) for nm, r, d in lv))[1]))

print("\n" + "=" * 100)
print("  C. NULLS AT THE RIGHT LEVEL for newunder FADE | notCUT (ROI %+.1f%%)" % (100 * froi(NOTCUT)))
print("=" * 100)
tgt = froi(NOTCUT)
ids = set(id(b) for b in NOTCUT)
for blocks, flat, lbl in ((gblocks, gflat, "GAME-block   "), (pblocks, pflat, "PLAYER-block ")):
    beat = 0; gap_beat = 0
    real_gap = froi(NOTCUT) - froi(CUT)
    for _ in range(T):
        lab = perm(blocks, flat)
        v = sum(-1.0 if lab[id(b)] else (b["oppod"] - 1) for b in NOTCUT) / len(NOTCUT)
        vc = sum(-1.0 if lab[id(b)] else (b["oppod"] - 1) for b in CUT) / len(CUT)
        if v >= tgt: beat += 1
        if (v - vc) >= real_gap: gap_beat += 1
    print("  %s p(cell ROI)          = %.4f" % (lbl, beat / T))
    print("  %s p(notCUT-CUT contrast %+.1fpp) = %.4f" % (lbl, 100 * real_gap, gap_beat / T))

print("\n" + "=" * 100)
print("  D. MECHANISM: the direction CONTRADICTS the board-wide line-move gradient")
print("=" * 100)
for bk, sel in (("CUT", lambda r: r["linemv"] is not None and r["linemv"] <= -0.5),
                ("notCUT", lambda r: r["linemv"] is not None and r["linemv"] > -0.5)):
    g = [r for r in B if sel(r)]
    print("  FULL BOARD %-7s n=%-5d over-rate %.1f%%" % (bk, len(g), 100 * sum(1 for r in g if r["over_won"]) / len(g)))
for bk, g in (("CUT", CUT), ("notCUT", NOTCUT)):
    print("  newunder   %-7s n=%-5d over-rate %.1f%%" % (bk, len(g), 100 * sum(1 for b in g if b["over_won"]) / len(g)))
print("  -> on the board a CUT line goes OVER more (53.6 vs 49.5). Inside newunder the ordering")
print("     REVERSES. The fade cell therefore needs an interaction story, not the known gradient.")

print("\n  market breakdown of newunder FADE | notCUT (coverage confound check):")
for mk in sorted(set(b["mk"] for b in NOTCUT)):
    g = [b for b in NOTCUT if b["mk"] == mk]
    if len(g) < 15: print("    %-4s n=%-3d --" % (mk, len(g))); continue
    print("    %-4s n=%-3d FADE %+6.1f%%  over-rate %.1f%%"
          % (mk, len(g), 100 * froi(g), 100 * sum(1 for b in g if b["over_won"]) / len(g)))
print("\n  per-player concentration (top 6 by count):")
cc = collections.Counter(b["pl"] for b in NOTCUT)
for pl, n in cc.most_common(6):
    g = [b for b in NOTCUT if b["pl"] == pl]
    print("    %-24s n=%-3d FADE %+7.1f%%" % (pl, n, 100 * froi(g)))
print("  distinct players %d, top player = %.0f%% of the cell" % (len(cc), 100 * cc.most_common(1)[0][1] / len(NOTCUT)))

print("\n" + "=" * 100)
print("  E. WALK-FORWARD: fit the bucket on games before date X, bet after")
print("=" * 100)
NUs = sorted(NU, key=lambda b: (b["date"], b["gt"]))
for cutd in ("20260715", "20260801", "20260810"):
    tr = [b for b in NUs if b["date"] < cutd]; te = [b for b in NUs if b["date"] >= cutd]
    if len(tr) < 60 or len(te) < 40: continue
    tn = [b for b in tr if b["mv"] > -0.5]
    en = [b for b in te if b["mv"] > -0.5]
    print("  split %s  train notCUT n=%-3d FADE %+6.1f%%   ->   TEST notCUT n=%-3d FADE %+6.1f%%"
          % (cutd, len(tn), 100 * froi(tn), len(en), 100 * froi(en)))
