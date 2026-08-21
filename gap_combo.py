# gap_combo.py - the sharp-divergence lead, fed properly, then combined.
# ---------------------------------------------------------------------------------------------
# fresh_hunt found "bet toward Pinnacle when 1xbet disagrees" pointing the right way but starved:
# 378 of 6471 quotes had a gap. The reason is now clear - pinn_snapshots.csv is 4300 pts rows and
# only 42 reb / 37 ast, so every combo market (pr, pra, pa, ra) fails to reconstruct. The signal
# was never thin; the SAMPLE was, and only for combos.
#
# Two repairs before any testing:
#   1 focus on pts, where sharp coverage actually exists
#   2 add bets_log.csv's `pinn` column - 4664 populated rows the engine stored at bet time and
#     that no analysis has ever used. Different capture path, same quantity.
#
# Then the RIGHT test. Cells throw away the ordering; the hypothesis is dose-response - the bigger
# the disagreement, the more wrong the soft book is. So: define the toward-sharp side for every
# quote, and correlate |gap| with that side's return. Trend test, player-block permuted.
#
# Then combinations, each with a reason:
#   gap x LINE MOVE   a stale line that hasn't moved is more likely to still be wrong
#   gap x TOTAL       yesterday's pace finding - does divergence matter more in slow games?
#   gap x CUSHION     is the gap just re-measuring the overshoot signal? (must be near-zero)
#   gap x LEAN        the book's own odds skew vs the sharp line
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260821)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
gof, oppof, dateof = {}, {}, {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    gof[(hm, t2)] = gid; gof[(aw, t2)] = gid
    oppof[(hm, t2)] = aw; oppof[(aw, t2)] = hm; dateof[t2] = d2
GL = collections.defaultdict(dict)
for r in load("gamelines.csv"):
    st = (r.get("start") or "")[:10].replace("-", "")
    tm = (r.get("teams") or "").split("|")
    if len(tm) != 2: continue
    ab = tuple(sorted(FULL.get(t.strip(), "") for t in tm))
    if "" in ab: continue
    cap, pts = ts(r.get("captured_utc")), f(r.get("points"))
    if not cap: continue
    s = GL[(st, ab)]
    if r.get("type") == "total" and pts is not None and ("tot" not in s or cap > s["tot"][0]):
        s["tot"] = (cap, pts)

# ---- sharp lines from BOTH sources ----------------------------------------------------------
pin = collections.defaultdict(list)
for r in load("pinn_snapshots.csv"):
    cap, ln = ts(r.get("captured_utc")), f(r.get("pinn_line"))
    pl, mk = (r.get("player") or "").lower(), r.get("market")
    if cap and ln is not None and pl and mk: pin[(pl, mk)].append((cap, ln, "snap"))
nlog = 0
for r in load("bets_log.csv"):
    ln = f(r.get("pinn"))
    cap = ts(r.get("captured_utc"))
    pl, mk = (r.get("player") or "").lower(), r.get("market")
    if cap and ln is not None and pl and mk:
        pin[(pl, mk)].append((cap, ln, "log")); nlog += 1
for v in pin.values(): v.sort(key=lambda x: x[0])
print(f"sharp reference lines: {sum(len(v) for v in pin.values())} rows "
      f"({nlog} from bets_log, the rest from pinn_snapshots)")
cov_mk = collections.Counter(mk for (pl, mk) in pin for _ in [0])
print("  markets with sharp coverage: " + ", ".join(
    f"{mk}:{sum(1 for (p2,m2),v in pin.items() if m2==mk for _ in v)}"
    for mk in ("pts", "reb", "ast", "pr", "pra", "pa", "ra")))
def sharp(pl, mk, gt):
    got = [x for x in pin.get((pl, mk), []) if x[0] <= gt and (gt-x[0]).total_seconds() < 30*3600]
    return got[-1][1] if got else None
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

Q = []
for (pl, mk, gt), sdq in side.items():
    if "Over" not in sdq or "Under" not in sdq: continue
    if abs(sdq["Over"][1] - sdq["Under"][1]) > 0.01: continue
    now = pgrow.get((pl, gt)); tm = teamof.get(pl)
    if not now or mk not in now or not tm: continue
    ln = sdq["Over"][1]
    if now[mk] == ln: continue
    sp = sharp(pl, mk, gt)
    if sp is None: continue
    gap = sp - ln                                   # + : sharp HIGHER -> 1xbet too low -> OVER
    tw = "o" if gap > 0 else "u"                    # the toward-sharp side
    gid = gof[(tm, gt)]; d2, t2, hm, aw = gmeta[gid]
    s = GL.get((d2, tuple(sorted((hm, aw)))), {})
    md = med_team(pl, mk, gt)
    pv = prevline.get((pl, mk, gt))
    Q.append(dict(pl=pl, mk=mk, gt=gt, gid=gid, tm=tm, date=d2, ln=ln, sp=sp, gap=gap, tw=tw,
                  o_od=sdq["Over"][2], u_od=sdq["Under"][2],
                  o_won=now[mk] > ln, u_won=now[mk] < ln,
                  ret=((sdq["Over"][2]-1) if now[mk] > ln else -1.0) if tw == "o"
                      else ((sdq["Under"][2]-1) if now[mk] < ln else -1.0),
                  won=(now[mk] > ln) if tw == "o" else (now[mk] < ln),
                  od=(sdq["Over"][2] if tw == "o" else sdq["Under"][2]),
                  tot=s.get("tot", (None, None))[1],
                  cush=(md-ln) if md is not None else None,
                  copied=(pv is not None and abs(ln-pv) < 0.01),
                  lean=sdq["Under"][2]-sdq["Over"][2]))
print(f"\n{len(Q)} quotes now have a sharp reference "
      f"(was 378) - by market: " + ", ".join(
      f"{k}:{v}" for k, v in collections.Counter(r['mk'] for r in Q).most_common()))
print("")
def roi(rows): return 100*sum(r["ret"] for r in rows)/len(rows) if rows else 0
def hitr(rows): return 100*sum(1 for r in rows if r["won"])/len(rows) if rows else 0
def pboot(rows, T=2500):
    bp = collections.defaultdict(list)
    for r in rows: bp[r["pl"]].append(r)
    k = list(bp); o = []
    for _ in range(T): o.append(roi([x for p in [random.choice(k) for _ in k] for x in bp[p]]))
    o.sort(); return o[int(T*.025)], o[int(T*.975)]
def show(rows, lbl, minn=40):
    if len(rows) < minn: print(f"    {lbl:<50} n={len(rows)} too few"); return
    lo, hi = pboot(rows)
    star = "  <<<" if lo > 0 else ""
    print(f"    {lbl:<50} n={len(rows):<5}{hitr(rows):>6.1f}%{roi(rows):>+8.1f}%  [{lo:+6.1f},{hi:+6.1f}]{star}")
def spearman(xs, ys):
    def rk(v):
        s = sorted(range(len(v)), key=lambda i: v[i]); r = [0]*len(v)
        for i, j in enumerate(s): r[j] = i
        return r
    a, b = rk(xs), rk(ys); ma, mb = statistics.mean(a), statistics.mean(b)
    num = sum((a[i]-ma)*(b[i]-mb) for i in range(len(a)))
    den = math.sqrt(sum((x-ma)**2 for x in a)*sum((y-mb)**2 for y in b))
    return num/den if den else 0.0

print("="*104)
print("  1. DOSE-RESPONSE: does a BIGGER disagreement pay more?  (toward-sharp side)")
print("="*104)
for lo_, hi_, lbl in ((0, 0.01, "books agree exactly (gap 0)"),
                      (0.01, 1.0, "gap 0.5"), (1.0, 2.0, "gap 1.0-1.5"),
                      (2.0, 99, "gap 2.0+")):
    show([r for r in Q if lo_ <= abs(r["gap"]) < hi_], lbl)
NZ = [r for r in Q if abs(r["gap"]) > 0.01]
if len(NZ) >= 60:
    rho = spearman([abs(r["gap"]) for r in NZ], [r["ret"] for r in NZ])
    bp = collections.defaultdict(list)
    for r in NZ: bp[r["pl"]].append(r)
    kk = list(bp); beat = 0; T = 4000
    for _ in range(T):
        vals = [abs(bp[k][0]["gap"]) for k in kk]; random.shuffle(vals)
        lab = dict(zip(kk, vals))
        if spearman([lab[r["pl"]] for r in NZ], [r["ret"] for r in NZ]) >= rho: beat += 1
    print(f"\n    |gap| vs toward-sharp return: rho = {rho:+.4f}   player-permutation p = {beat/T:.4f}")
print("")
print("="*104)
print("  2. DIRECTION - is one side of the disagreement better than the other?")
print("="*104)
show([r for r in Q if r["gap"] >= 1.0], "  sharp HIGHER by 1+  -> bet OVER")
show([r for r in Q if r["gap"] <= -1.0], "  sharp LOWER by 1+   -> bet UNDER")
print("")
print("="*104)
print("  3. COMBINATIONS - each with a reason")
print("="*104)
BIG = [r for r in Q if abs(r["gap"]) >= 1.0]
print(f"  base: |gap|>=1.0, n={len(BIG)}, ROI {roi(BIG):+.1f}%")
show([r for r in BIG if r["copied"]], "    + line COPIED from her last game (stale)")
show([r for r in BIG if not r["copied"]], "    + line moved since last game")
if any(r["tot"] is not None for r in BIG):
    tv = sorted(r["tot"] for r in BIG if r["tot"] is not None)
    if len(tv) >= 40:
        tm_ = tv[len(tv)//2]
        show([r for r in BIG if r["tot"] is not None and r["tot"] <= tm_], f"    + game total LOW (<= {tm_:.0f})")
        show([r for r in BIG if r["tot"] is not None and r["tot"] > tm_], f"    + game total HIGH")
cv = [r for r in BIG if r["cush"] is not None]
if len(cv) >= 40:
    print(f"    confound check: corr(|gap|, cushion) = "
          f"{spearman([abs(r['gap']) for r in cv], [r['cush'] for r in cv]):+.3f}  (want ~0)")
show([r for r in BIG if r["lean"] * (1 if r["tw"] == "o" else -1) > 0.02],
     "    + book's odds lean AGREES with sharp")
show([r for r in BIG if r["lean"] * (1 if r["tw"] == "o" else -1) < -0.02],
     "    + book's odds lean DISAGREES with sharp")
print("")
print("="*104)
print("  4. OUT OF SAMPLE")
print("="*104)
dts = sorted({r["date"] for r in BIG}); cut = dts[len(dts)//2]
show([r for r in BIG if r["date"] < cut], f"    |gap|>=1, first half (< {cut})", minn=25)
show([r for r in BIG if r["date"] >= cut], f"    |gap|>=1, second half", minn=25)
