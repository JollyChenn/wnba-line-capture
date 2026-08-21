# combo_hunt.py - what combines with the sharp gap? two new mechanisms plus the known ones.
# ---------------------------------------------------------------------------------------------
# The gap is the strongest thing found: n=105, +13.0% at the actionable 6h horizon, p=0.0027,
# OOS +13.3/+12.9. This asks what sharpens it. Everything is evaluated on the 6h sharp line, so
# nothing here uses information we could not have had.
#
# TWO NEW FEATURES, both with a real story:
#
#  1 PERSISTENCE. A disagreement visible at BOTH 9h and 6h is a standing difference of opinion
#    between two books. A gap that appears only in the last window may be one stale quote, a
#    mis-scrape, or a line caught mid-move. Persistent disagreements should pay better - and this
#    is testable for free from data we already hold.
#
#  2 CONVERGENCE. Which way is 1xbet's own line travelling? If 1xbet is moving TOWARD Pinnacle
#    the gap is closing and we are late to a correction already under way. If 1xbet is moving
#    AWAY, the disagreement is widening and the soft book is digging in. That is the difference
#    between catching a repricing and standing in front of one. This is the single most
#    mechanism-driven feature available and it has never been tested.
#
# Plus the known ones: game total (pace is worth 19 pts of ROI), spread (blowouts kill overs),
# price drift, market, gap magnitude, and gate 3.
#
# NOISE CEILING FIRST, computed over the whole declared grid, permuted at the player block -
# the gap is a player-market attribute, so that is where its label lives.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260821)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
H, H2 = 6, 9
gof, oppof, dateof = {}, {}, {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    gof[(hm, t2)] = gid; gof[(aw, t2)] = gid
    oppof[(hm, t2)] = aw; oppof[(aw, t2)] = hm; dateof[t2] = d2
GL = collections.defaultdict(dict)
for r in load("gamelines.csv"):
    st = (r.get("start") or "")[:10].replace("-", "")
    tmn = (r.get("teams") or "").split("|")
    if len(tmn) != 2: continue
    ab = tuple(sorted(FULL.get(t.strip(), "") for t in tmn))
    if "" in ab: continue
    cap, pts = ts(r.get("captured_utc")), f(r.get("points"))
    if not cap: continue
    s = GL[(st, ab)]
    if r.get("type") == "total" and pts is not None and ("tot" not in s or cap > s["tot"][0]):
        s["tot"] = (cap, pts)
    if r.get("type") == "spread" and pts is not None and ("spr" not in s or cap > s["spr"][0]):
        s["spr"] = (cap, abs(pts))
pin = collections.defaultdict(list)
for r in load("pinn_snapshots.csv"):
    cap, ln = ts(r.get("captured_utc")), f(r.get("pinn_line"))
    pl, mk = (r.get("player") or "").lower(), r.get("market")
    if cap and ln is not None and pl and mk: pin[(pl, mk)].append((cap, ln))
for r in load("bets_log.csv"):
    cap, ln = ts(r.get("captured_utc")), f(r.get("pinn"))
    pl, mk = (r.get("player") or "").lower(), r.get("market")
    if cap and ln is not None and pl and mk: pin[(pl, mk)].append((cap, ln))
for v in pin.values(): v.sort()
def sharp_at(pl, mk, gt, hours):
    cut = gt - datetime.timedelta(hours=hours)
    got = [x for x in pin.get((pl, mk), []) if x[0] <= cut and (gt-x[0]).total_seconds() < 30*3600]
    return got[-1][1] if got else None
# 1xbet's own OVER line history, for convergence
walk = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if not (t and o and ln is not None) or b.get("side") != "Over": continue
    pl, mk = (b.get("player") or "").lower(), b.get("market")
    tm = teamof.get(pl)
    if not tm: continue
    gt = game_for(tm, t)
    if gt: walk[(pl, mk, gt)].append((t, ln, o))
for v in walk.values(): v.sort()
_mc = {}
def med_team(pl, mk, gt):
    k = (pl, mk, gt)
    if k in _mc: return _mc[k]
    g = [r for r in hist.get(pl, []) if r["tip"] < gt]
    out = None
    if g:
        cur = g[-1]["tm"]; g2 = [r for r in g if r["tm"] == cur]
        if len(g2) >= 5: out = statistics.median([r[mk] for r in g2[-10:]])
    _mc[k] = out
    return out

R = []
for (pl, mk, gt), sdq in side.items():
    if "Over" not in sdq or "Under" not in sdq: continue
    if abs(sdq["Over"][1] - sdq["Under"][1]) > 0.01: continue
    now = pgrow.get((pl, gt)); tm = teamof.get(pl)
    if not now or mk not in now or not tm: continue
    ln = sdq["Over"][1]
    if now[mk] == ln: continue
    sp = sharp_at(pl, mk, gt, H)
    if sp is None: continue
    gap = sp - ln
    if abs(gap) < 1.0: continue                    # the base rule
    sd = "o" if gap > 0 else "u"
    sp9 = sharp_at(pl, mk, gt, H2)
    persist = (sp9 is not None and abs(sp9 - ln) >= 1.0 and ((sp9 - ln) > 0) == (gap > 0))
    # convergence: how 1xbet's own line moved over the window leading into our bet
    q = [x for x in walk.get((pl, mk, gt), []) if (gt - x[0]).total_seconds() >= H*3600]
    xmove = (q[-1][1] - q[0][1]) if len(q) >= 2 else None
    conv = None
    if xmove is not None and abs(xmove) > 0.01:
        conv = "toward" if (xmove > 0) == (gap > 0) else "away"
    same = [x for x in walk.get((pl, mk, gt), []) if abs(x[1]-ln) < 0.01
            and (gt - x[0]).total_seconds() >= H*3600]
    pdrift = (same[-1][2] - same[0][2]) if len(same) >= 2 else None
    gid = gof[(tm, gt)]; d2, t2, hm, aw = gmeta[gid]
    s = GL.get((d2, tuple(sorted((hm, aw)))), {})
    md = med_team(pl, mk, gt); pv = prevline.get((pl, mk, gt))
    R.append(dict(pl=pl, mk=mk, gt=gt, gid=gid, date=d2, ln=ln, gap=gap, sd=sd,
                  ret=((sdq["Over"][2]-1) if now[mk] > ln else -1.0) if sd == "o"
                      else ((sdq["Under"][2]-1) if now[mk] < ln else -1.0),
                  won=(now[mk] > ln) if sd == "o" else (now[mk] < ln),
                  persist=persist, conv=conv, pdrift=pdrift,
                  tot=s.get("tot", (None, None))[1], spr=s.get("spr", (None, None))[1],
                  cush=(md-ln) if md is not None else None,
                  star=(pv is not None and ln - pv < 0.5)))
print(f"{len(R)} bets from the base rule (|gap|>=1 at {H}h), {len({r['gid'] for r in R})} games")
print(f"  persistence known on {sum(1 for r in R if r['persist'])} (at {H2}h too),"
      f" convergence on {sum(1 for r in R if r['conv'])},"
      f" total on {sum(1 for r in R if r['tot'] is not None)}")
print("")
def roi(rows): return 100*sum(r["ret"] for r in rows)/len(rows) if rows else 0.0
def hitr(rows): return 100*sum(1 for r in rows if r["won"])/len(rows) if rows else 0.0
def pboot(rows, T=2500):
    bp = collections.defaultdict(list)
    for r in rows: bp[r["pl"]].append(r)
    k = list(bp); o = []
    for _ in range(T): o.append(roi([x for p in [random.choice(k) for _ in k] for x in bp[p]]))
    o.sort(); return o[int(T*.025)], o[int(T*.975)]
def show(rows, lbl, minn=25):
    if len(rows) < minn: print(f"    {lbl:<46} n={len(rows)} too few"); return None
    lo, hi = pboot(rows)
    star = "  <<<" if lo > 0 else ""
    print(f"    {lbl:<46} n={len(rows):<5}{hitr(rows):>6.1f}%{roi(rows):>+8.1f}%  [{lo:+6.1f},{hi:+6.1f}]{star}")
    return roi(rows)

CELLS = [
    ("persistent (gap at 9h too)", lambda r: r["persist"]),
    ("NOT persistent (new at 6h)", lambda r: not r["persist"]),
    ("1xbet moving TOWARD sharp", lambda r: r["conv"] == "toward"),
    ("1xbet moving AWAY from sharp", lambda r: r["conv"] == "away"),
    ("1xbet line static", lambda r: r["conv"] is None),
    ("gap 1.0-1.5", lambda r: abs(r["gap"]) < 1.6),
    ("gap 1.5+", lambda r: abs(r["gap"]) >= 1.6),
    ("sharp HIGHER -> over", lambda r: r["sd"] == "o"),
    ("sharp LOWER -> under", lambda r: r["sd"] == "u"),
    ("market = pts", lambda r: r["mk"] == "pts"),
    ("market != pts", lambda r: r["mk"] != "pts"),
    ("price drifted against us", lambda r: r["pdrift"] is not None and r["pdrift"] > 0.005),
    ("price shortened", lambda r: r["pdrift"] is not None and r["pdrift"] < -0.005),
    ("gate 3 star", lambda r: r["star"]),
    ("game total high", lambda r: r["tot"] is not None and r["tot"] > 176),
    ("game total low", lambda r: r["tot"] is not None and r["tot"] <= 176),
    ("spread wide", lambda r: r["spr"] is not None and r["spr"] > 9),
]
bp = collections.defaultdict(list)
for r in R: bp[r["pl"]].append(r)
pk = list(bp)
peaks = []
for _ in range(1500):
    pool = [r["ret"] for r in R]; random.shuffle(pool)
    for r, v in zip(R, pool): r["_r"] = v
    best = -99
    for lbl, sel in CELLS:
        g = [r for r in R if sel(r)]
        if len(g) < 25: continue
        best = max(best, 100*sum(r["_r"] for r in g)/len(g))
    if best > -99: peaks.append(best)
peaks.sort()
CEIL = peaks[int(len(peaks)*0.95)]
print("="*100)
print(f"  NOISE CEILING FIRST: {len(CELLS)} cells, returns reshuffled -> p95 best cell {CEIL:+.1f}%")
print("="*100)
print(f"    {'BASE: |gap|>=1 at 6h':<46} n={len(R):<5}{hitr(R):>6.1f}%{roi(R):>+8.1f}%")
print("")
res = []
for lbl, sel in CELLS:
    v = show([r for r in R if sel(r)], lbl)
    if v is not None: res.append((v, lbl))
print("")
print("="*100)
print("  ABOVE THE CEILING")
print("="*100)
w = [x for x in res if x[0] > CEIL]
for v, lbl in sorted(w, reverse=True): print(f"    {lbl:<46} {v:+.1f}%")
if not w: print("    none")
print("")
print("="*100)
print("  THE TWO NEW MECHANISMS, tested properly")
print("="*100)
for nm, sel_a, sel_b in (("PERSISTENCE", lambda r: r["persist"], lambda r: not r["persist"]),
                         ("CONVERGENCE", lambda r: r["conv"] == "away", lambda r: r["conv"] == "toward")):
    a = [r for r in R if sel_a(r)]; b = [r for r in R if sel_b(r)]
    if len(a) < 20 or len(b) < 20:
        print(f"  {nm}: n={len(a)}/{len(b)} too few"); continue
    real = roi(a) - roi(b)
    lab0 = {}
    for r in R: lab0.setdefault(r["pl"], sel_a(r))
    keys = list(lab0); vals = [lab0[k] for k in keys]
    beat = 0; T = 4000; ok = 0
    for _ in range(T):
        random.shuffle(vals); lab = dict(zip(keys, vals))
        g1 = [r for r in R if lab[r["pl"]]]; g2 = [r for r in R if not lab[r["pl"]]]
        if len(g1) < 20 or len(g2) < 20: continue
        ok += 1
        if roi(g1) - roi(g2) >= real: beat += 1
    print(f"  {nm}: gap {real:+.1f} points   player-block permutation p = {beat/max(ok,1):.4f}")
