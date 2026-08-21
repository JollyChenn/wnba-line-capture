# gamemkt.py - do the GAME markets (total / spread / moneyline) predict player prop results?
# ---------------------------------------------------------------------------------------------
# total_fix.py established two facts that frame this exactly:
#   * the REALISED game score swings player overs by ~19 points of ROI (low -17.0 / high +2.0)
#   * the BOARD's posted player lines carry no advance signal of it (per-line mean: flat)
# So the question is whether the bookmakers' own GAME markets - which exist before tip and are
# sharpened by real money - forecast the pace that the player board cannot. If they do, even
# partially, that is a pre-tip feature worth more than every filter tried this season.
#
# Sources, joined by (date, team-pair):
#   gamelines.csv        Pinnacle guest API captures, 2026-07-11 onward (sharp)
#   xbet_gamelines.csv   1xbet's own game markets, 2026-08-16 onward (small, same book as props)
# Coverage is partial (no capture before Jul 11), so every split reports its own n and the
# noise ceiling is computed FIRST at the game level on exactly the covered subset.
#
# Features per game, all knowable pre-tip (last capture BEFORE tip, never after):
#   TOTAL   the posted game total. 160 = grind, 175+ = track meet.
#   SPREAD  absolute favourite margin. Wide = blowout risk = 4th-quarter benching.
#   ML      favourite win prob from the moneyline (vig-split). "How lopsided is this game?"
# Questions, in order:
#   1 does the TOTAL predict over vs under results on the player board? (both sides priced real)
#   2 does the SPREAD? and is it the favourite's players or the dog's who suffer in blowouts?
#   3 does the ML add anything beyond the spread (they encode the same thing, so probably not)?
#   4 do any of these move MODEL S bets specifically?
#   5 does the total actually FORECAST the realised score here (calibration sanity check)?
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260821)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
SIGS = ("flip", "hotover", "overshoot"); BET_MKTS = ("pra", "pr", "pts")
ALLMK = ("pts", "pr", "pra", "pa", "ra", "reb", "ast")

tip_on, gof, oppof, dateof = {}, {}, {}, {}
realtot, realmarg = {}, {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    tip_on[(hm, d2)] = t2; tip_on[(aw, d2)] = t2
    gof[(hm, t2)] = gid; gof[(aw, t2)] = gid
    oppof[(hm, t2)] = aw; oppof[(aw, t2)] = hm
    dateof[t2] = d2
for g in load("data/games_2026.csv"):
    a_, h_ = f(g.get("away_score")), f(g.get("home_score"))
    if a_ is not None and h_ is not None:
        realtot[g.get("game_id")] = a_ + h_
        realmarg[g.get("game_id")] = abs(h_ - a_)

# ---- game-market features per (date, teampair), LAST capture before tip --------------------
# Pinnacle (gamelines.csv): teams are full names, prices American, spread points signed per side
GL = collections.defaultdict(dict)   # (date, abpair) -> {tot, spr, mlprob}
for r in load("gamelines.csv"):
    st = (r.get("start") or "")[:10].replace("-", "")
    tm = (r.get("teams") or "").split("|")
    if len(tm) != 2: continue
    ab = tuple(sorted(FULL.get(t.strip(), "") for t in tm))
    if "" in ab: continue
    cap, pts = ts(r.get("captured_utc")), f(r.get("points"))
    if not cap: continue
    s = GL[(st, ab)]
    ty = r.get("type")
    if ty == "total" and pts is not None and ("tot" not in s or cap > s["tot"][0]):
        s["tot"] = (cap, pts)
    if ty == "spread" and pts is not None and ("spr" not in s or cap > s["spr"][0]):
        s["spr"] = (cap, abs(pts))
    if ty == "moneyline":
        pr = (r.get("prices") or "").split(",")
        if len(pr) == 2 and pr[0] and pr[1]:
            p1, p2 = am(pr[0]), am(pr[1])
            if p1 is not None and p2 is not None and p1 + p2 > 0:
                fav = max(p1, p2) / (p1 + p2)          # vig-split favourite probability
                if "ml" not in s or cap > s["ml"][0]: s["ml"] = (cap, fav)
def gfeat(date, hm, aw):
    s = GL.get((date, tuple(sorted((hm, aw)))), {})
    return (s.get("tot", (None, None))[1], s.get("spr", (None, None))[1],
            s.get("ml", (None, None))[1])

# ---- every gradable two-sided player quote, tagged with its game's market ------------------
Q = []
for (pl, mk, gt), sdq in side.items():
    if mk not in ALLMK or "Over" not in sdq or "Under" not in sdq: continue
    if abs(sdq["Over"][1] - sdq["Under"][1]) > 0.01: continue
    now = pgrow.get((pl, gt)); tm = teamof.get(pl)
    if not now or mk not in now or not tm: continue
    ln = sdq["Over"][1]
    if now[mk] == ln: continue
    op = oppof.get((tm, gt)); gid = gof[(tm, gt)]
    d2, t2, hm, aw = gmeta[gid]
    tot, spr, ml = gfeat(d2, hm, aw)
    pv = prevline.get((pl, mk, gt))
    # is HER team the ML favourite? resolve via spread side if possible - fall back to ml>0.5 fav side unknown
    Q.append(dict(pl=pl, mk=mk, gt=gt, gid=gid, tm=tm, date=d2,
                  ln=ln, o_od=sdq["Over"][2], u_od=sdq["Under"][2],
                  o_won=now[mk] > ln, u_won=now[mk] < ln,
                  star=(pv is not None and ln - pv < 0.5),
                  tot=tot, spr=spr, ml=ml,
                  rt=realtot.get(gid), rm=realmarg.get(gid)))
COV = [r for r in Q if r["tot"] is not None]
print(f"{len(Q)} two-sided player quotes; {len(COV)} in games with a Pinnacle total "
      f"({len({r['gid'] for r in COV})} games, from {min(r['date'] for r in COV)})")
print("")

def roi(rows, sd="o"):
    if not rows: return 0.0
    wk, ok = sd+"_won", sd+"_od"
    return 100*sum((r[ok]-1) if r[wk] else -1.0 for r in rows)/len(rows)
def hit(rows, sd="o"): return 100*sum(1 for r in rows if r[sd+"_won"])/len(rows) if rows else 0
def gboot(rows, sd="o", T=2000):
    bg = collections.defaultdict(list)
    for r in rows: bg[r["gid"]].append(r)
    k = list(bg); o = []
    for _ in range(T): o.append(roi([x for p in [random.choice(k) for _ in k] for x in bg[p]], sd))
    o.sort(); return o[int(T*.025)], o[int(T*.975)]
def show(rows, lbl, sd="o", minn=80):
    if len(rows) < minn: print(f"    {lbl:<46} n={len(rows)} too few"); return
    lo, hi = gboot(rows, sd)
    print(f"    {lbl:<46} n={len(rows):<5}{hit(rows,sd):>6.1f}%{roi(rows,sd):>+8.1f}%  95CI [{lo:+6.1f},{hi:+6.1f}]")

# ---- ceiling FIRST: game-label permutation over the whole grid we are about to run ----------
# every split below assigns each GAME to a bucket by a game-level feature; the null relabels
# games. 3 features x 3 buckets x 2 sides = 18 primary cells.
bg = collections.defaultdict(list)
for r in COV: bg[r["gid"]].append(r)
gk = list(bg)
peaks = []
for _ in range(600):
    lab = {g: random.random() for g in gk}
    best = -99
    for _ in range(18):
        a, b = sorted((random.random(), random.random()))
        pick = [x for g in gk if a <= lab[g] < b for x in bg[g]]
        if len(pick) >= 80:
            best = max(best, roi(pick, "o"), roi(pick, "u"))
    if best > -99: peaks.append(best)
peaks.sort()
CEIL = peaks[int(len(peaks)*0.95)]
print("="*100)
print(f"  NOISE CEILING FIRST: random game-buckets of the covered set, 18 cells/trial,")
print(f"  best cell reaches ROI {CEIL:+.1f}% at p95 by luck alone. That is the bar.")
print("="*100)
print("")

print("="*100)
print("  1. THE TOTAL - your 'line at 160' question  (WNBA totals run ~155-175)")
print("="*100)
v = sorted(r["tot"] for r in COV)
t1, t2_ = v[len(v)//3], v[2*len(v)//3]
print(f"  terciles at {t1:.1f} / {t2_:.1f}")
for nm, sel in ((f"total LOW  (<= {t1:.1f})", lambda r: r["tot"] <= t1),
                (f"total MID", lambda r: t1 < r["tot"] <= t2_),
                (f"total HIGH (> {t2_:.1f})", lambda r: r["tot"] > t2_)):
    g = [r for r in COV if sel(r)]
    show(g, nm + "  OVERS ", "o")
    show(g, " " * len(nm) + "  UNDERS", "u")
print("")
print("="*100)
print("  2. THE SPREAD - wide spread = blowout risk")
print("="*100)
SP = [r for r in Q if r["spr"] is not None]
v = sorted(r["spr"] for r in SP)
s1, s2_ = v[len(v)//3], v[2*len(v)//3]
print(f"  terciles at {s1:.1f} / {s2_:.1f}")
for nm, sel in ((f"spread TIGHT (<= {s1:.1f})", lambda r: r["spr"] <= s1),
                (f"spread MID", lambda r: s1 < r["spr"] <= s2_),
                (f"spread WIDE (> {s2_:.1f})", lambda r: r["spr"] > s2_)):
    g = [r for r in SP if sel(r)]
    show(g, nm + "  OVERS ", "o")
    show(g, " " * len(nm) + "  UNDERS", "u")
print("")
print("  did wide-spread games actually BLOW OUT? (realised margin by spread tercile)")
for nm, sel in (("tight", lambda r: r["spr"] <= s1), ("mid", lambda r: s1 < r["spr"] <= s2_),
                ("wide", lambda r: r["spr"] > s2_)):
    g = {r["gid"]: r["rm"] for r in SP if sel(r) and r["rm"] is not None}
    if g: print(f"    {nm:<6} games: mean realised margin {statistics.mean(g.values()):5.1f}  (n={len(g)})")
print("")
print("="*100)
print("  3. THE MONEYLINE - beyond what the spread already says")
print("="*100)
ML = [r for r in Q if r["ml"] is not None]
v = sorted(r["ml"] for r in ML)
m1, m2_ = v[len(v)//3], v[2*len(v)//3]
print(f"  favourite prob terciles at {m1:.3f} / {m2_:.3f}")
for nm, sel in ((f"close game (fav <= {m1:.0%})", lambda r: r["ml"] <= m1),
                (f"clear fav", lambda r: m1 < r["ml"] <= m2_),
                (f"lopsided (fav > {m2_:.0%})", lambda r: r["ml"] > m2_)):
    g = [r for r in ML if sel(r)]
    show(g, nm + "  OVERS ", "o")
    show(g, " " * len(nm) + "  UNDERS", "u")
print("")
print("="*100)
print("  4. MODEL S BETS SPECIFICALLY")
print("="*100)
MSQ = []
for r in load("graded_bets.csv"):
    if (r.get("result") or "").upper() not in ("WIN", "LOSS"): continue
    src, mk, pl = (r.get("src") or ""), (r.get("market") or ""), (r.get("player") or "").lower()
    if src not in SIGS or mk not in BET_MKTS: continue
    tm = teamof.get(pl)
    gt = tip_on.get((tm, r.get("date") or "")) if tm else None
    if not gt: continue
    q = next((x for x in Q if x["pl"] == pl and x["mk"] == mk and x["gt"] == gt), None)
    if q and q["star"]: MSQ.append(q)
seen = {}
for r in sorted(MSQ, key=lambda x: -x["o_od"]): seen.setdefault((r["pl"], r["gt"]), r)
MSQ = list(seen.values())
mst = [r for r in MSQ if r["tot"] is not None]
print(f"  Model S bets with a Pinnacle total: {len(mst)} of {len(MSQ)}")
if len(mst) >= 24:
    med = statistics.median(r["tot"] for r in mst)
    show([r for r in mst if r["tot"] <= med], f"  total below median ({med:.1f})", "o", minn=10)
    show([r for r in mst if r["tot"] > med],  f"  total above median", "o", minn=10)
msp = [r for r in MSQ if r["spr"] is not None]
if len(msp) >= 24:
    med = statistics.median(r["spr"] for r in msp)
    show([r for r in msp if r["spr"] <= med], f"  spread below median ({med:.1f})", "o", minn=10)
    show([r for r in msp if r["spr"] > med],  f"  spread above median", "o", minn=10)
print("")
print("="*100)
print("  5. SANITY: does the Pinnacle total even forecast the realised score here?")
print("="*100)
cal = [(r["tot"], r["rt"]) for r in {r["gid"]: r for r in COV if r["rt"] is not None}.values()]
if len(cal) >= 20:
    xs, ys = [c[0] for c in cal], [c[1] for c in cal]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((x-mx)*(y-my) for x, y in cal)
    den = math.sqrt(sum((x-mx)**2 for x in xs) * sum((y-my)**2 for y in ys))
    print(f"  {len(cal)} games: mean posted total {mx:.1f}, mean realised {my:.1f},"
          f" correlation r = {num/den if den else 0:+.3f}")
    lo = [y for x, y in cal if x <= t1]; hi = [y for x, y in cal if x > t2_]
    if lo and hi:
        print(f"  posted-LOW games realised {statistics.mean(lo):.1f};"
              f" posted-HIGH realised {statistics.mean(hi):.1f}")
    print("  if r is near zero the total cannot help player props no matter what the buckets say.")
