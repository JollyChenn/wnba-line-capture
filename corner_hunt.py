# corner_hunt.py - three corners nobody has opened: implied volatility, raise magnitude, and
# the injury-news latency window.
# ---------------------------------------------------------------------------------------------
#  A  VOLATILITY & SKEW. The book posts every player's line with roughly the same odds template
#     (~1.85/1.85). But players are not the same distribution: some produce 18-19-20 every night,
#     some produce 8 or 30. And skewed producers have mean != median - if the book anchors on a
#     mean-flavoured projection while the .5 line settles at the 50% point (the MEDIAN), then for
#     right-skewed players the line sits high (bet under) and for left-skewed low (bet over).
#     Two features, both from her own box history, both never tested board-wide:
#       vol10  = sd of her last 10 in the stat, scaled by the line
#       skew   = mean10 - median10 (right skew positive)
#
#  B  RAISE MAGNITUDE. Gate 3 treats +0.5 and +4.0 identically: both "raised", both skipped. But
#     a small raise is the book tracking form, while a HUGE raise is the book chasing one big
#     game. If big raises overshoot, their UNDER at the raised line should pay, and it should be
#     dose-responsive in the size of the raise. Priced at the real under quote, never 1/over.
#
#  C  INJURY LATENCY. injuries_log.csv holds 887 timestamped status flags; the board holds
#     timestamped quotes. When a rotation player is first flagged OUT, her teammates' lines
#     should rise (more usage available). The corner: quotes captured AFTER the flag but where
#     the line has NOT yet moved from its pre-flag level - the book is late. Bet teammates' overs
#     in that window. This is the propagation family - the only family that has ever worked -
#     applied to news rather than to another book.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260822)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
gof, oppof, dateof = {}, {}, {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    gof[(hm, t2)] = gid; gof[(aw, t2)] = gid
    oppof[(hm, t2)] = aw; oppof[(aw, t2)] = hm; dateof[t2] = d2
def hist_stats(pl, mk, gt):
    g = [r for r in hist.get(pl, []) if r["tip"] < gt]
    if not g: return None
    cur = g[-1]["tm"]; g2 = [r for r in g if r["tm"] == cur]
    if len(g2) < 6: return None
    v = [r[mk] for r in g2[-10:]]
    return dict(med=statistics.median(v), mean=statistics.mean(v),
                sd=statistics.pstdev(v), n=len(v))

Q = []
for (pl, mk, gt), sdq in side.items():
    if "Over" not in sdq or "Under" not in sdq: continue
    if abs(sdq["Over"][1] - sdq["Under"][1]) > 0.01: continue
    now = pgrow.get((pl, gt)); tm = teamof.get(pl)
    if not now or mk not in now or not tm: continue
    ln = sdq["Over"][1]
    if now[mk] == ln: continue
    hs = hist_stats(pl, mk, gt)
    if not hs or hs["sd"] < 0.1: continue
    pv = prevline.get((pl, mk, gt))
    Q.append(dict(pl=pl, mk=mk, gt=gt, gid=gof[(tm, gt)], tm=tm, date=dateof.get(gt, ""),
                  ln=ln, o_od=sdq["Over"][2], u_od=sdq["Under"][2],
                  o_won=now[mk] > ln, u_won=now[mk] < ln,
                  med=hs["med"], sd=hs["sd"], relvol=hs["sd"]/max(ln, 1),
                  skew=hs["mean"] - hs["med"],
                  raise_=(ln - pv) if pv is not None else None))
def ret(r, sd_): return ((r[sd_+"_od"]-1) if r[sd_+"_won"] else -1.0)
def roi(rows, sd_): return 100*sum(ret(r, sd_) for r in rows)/len(rows) if rows else 0.0
def hitr(rows, sd_): return 100*sum(1 for r in rows if r[sd_+"_won"])/len(rows) if rows else 0.0
def pboot(rows, sd_, T=2000):
    bp = collections.defaultdict(list)
    for r in rows: bp[r["pl"]].append(r)
    k = list(bp); o = []
    for _ in range(T): o.append(roi([x for p in [random.choice(k) for _ in k] for x in bp[p]], sd_))
    o.sort(); return o[int(T*.025)], o[int(T*.975)]
def show(rows, lbl, sd_, minn=50):
    if len(rows) < minn: print(f"    {lbl:<52} n={len(rows)} too few"); return None
    lo, hi = pboot(rows, sd_)
    star = "  <<<" if lo > 0 else ""
    print(f"    {lbl:<52} n={len(rows):<5}{hitr(rows,sd_):>6.1f}%{roi(rows,sd_):>+8.1f}%  [{lo:+6.1f},{hi:+6.1f}]{star}")
    return roi(rows, sd_)
print(f"{len(Q)} two-sided quotes with team-filtered history")
print("")
print("="*104)
print("  A. VOLATILITY & SKEW")
print("="*104)
v = sorted(r["relvol"] for r in Q); v1, v2_ = v[len(v)//3], v[2*len(v)//3]
print(f"  relative volatility terciles at {v1:.3f} / {v2_:.3f}")
for nm, sel in (("STEADY players", lambda r: r["relvol"] <= v1),
                ("mid", lambda r: v1 < r["relvol"] <= v2_),
                ("WILD players", lambda r: r["relvol"] > v2_)):
    g = [r for r in Q if sel(r)]
    print(f"  {nm}")
    show(g, "  OVER", "o"); show(g, "  UNDER", "u")
sk = sorted(r["skew"] for r in Q); s1, s2_ = sk[len(sk)//3], sk[2*len(sk)//3]
print("")
print(f"  skew (mean minus median) terciles at {s1:+.2f} / {s2_:+.2f}")
show([r for r in Q if r["skew"] >= 1.0 and r["ln"] >= r["med"] + 0.5],
     "RIGHT-skewed, line above median -> UNDER", "u")
show([r for r in Q if r["skew"] <= -1.0 and r["ln"] <= r["med"] - 0.5],
     "LEFT-skewed, line below median -> OVER", "o")
show([r for r in Q if abs(r["skew"]) < 0.5], "symmetric players (control) -> OVER", "o")
print("")
print("="*104)
print("  B. RAISE MAGNITUDE - is a HUGE raise an overreaction? (UNDER at the real under price)")
print("="*104)
RZ = [r for r in Q if r["raise_"] is not None and r["raise_"] >= 0.5]
print(f"  {len(RZ)} raised lines")
for lo_, hi_, lbl in ((0.5, 1.5, "raised +0.5 to +1.0"), (1.5, 2.5, "raised +1.5 to +2.0"),
                      (2.5, 99, "raised +2.5 or more")):
    show([r for r in RZ if lo_ <= r["raise_"] < hi_], f"{lbl} -> UNDER", "u")
def spearman(xs, ys):
    def rk(vv):
        s = sorted(range(len(vv)), key=lambda i: vv[i]); r = [0]*len(vv)
        for i, j in enumerate(s): r[j] = i
        return r
    a, b = rk(xs), rk(ys); ma, mb = statistics.mean(a), statistics.mean(b)
    num = sum((a[i]-ma)*(b[i]-mb) for i in range(len(a)))
    den = math.sqrt(sum((x-ma)**2 for x in a)*sum((y-mb)**2 for y in b))
    return num/den if den else 0.0
if len(RZ) >= 100:
    rho = spearman([r["raise_"] for r in RZ], [ret(r, "u") for r in RZ])
    bp = collections.defaultdict(list)
    for r in RZ: bp[r["pl"]].append(r)
    kk = list(bp); beat = 0; T = 3000
    for _ in range(T):
        vals = [bp[k][0]["raise_"] for k in kk]; random.shuffle(vals)
        lab = dict(zip(kk, vals))
        if spearman([lab[r["pl"]] for r in RZ], [ret(r, "u") for r in RZ]) >= rho: beat += 1
    print(f"  dose-response: rho(raise size, under return) = {rho:+.4f}  player-perm p = {beat/T:.4f}")
print("")
print("="*104)
print("  C. INJURY LATENCY - teammates' overs after an OUT flag, before the line moves")
print("="*104)
outs = []
seenflag = set()
for r in load("injuries_log.csv"):
    if (r.get("status") or "").lower() != "out": continue
    t = ts(r.get("captured_utc"))
    pl = (r.get("player") or "").lower()
    tmfull = r.get("team") or ""
    ab = FULL.get(tmfull.strip(), "")
    if not (t and pl and ab): continue
    k = (pl, t.date().isoformat())
    if k in seenflag: continue                       # first flag only - the news moment
    seenflag.add(k)
    outs.append((t, pl, ab))
print(f"  {len(outs)} first-time OUT flags with a team")
# for each flag: teammates with a game within 30h, quote AFTER flag, line unchanged vs pre-flag
walk = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if not (t and o and ln is not None) or b.get("side") != "Over": continue
    pl, mk = (b.get("player") or "").lower(), b.get("market")
    tm = teamof.get(pl)
    if not tm: continue
    gt = game_for(tm, t)
    if gt: walk[(pl, mk, gt)].append((t, ln, o))
for vv in walk.values(): vv.sort()
LAT = []
usedkey = set()
for t0, outpl, ab in outs:
    # was she actually a rotation player? median minutes >= 15
    mg = [r["min"] for r in hist.get(outpl, []) if r["tip"] < t0 + datetime.timedelta(hours=30)]
    if len(mg) < 4 or statistics.median(mg[-8:]) < 15: continue
    for (pl, mk, gt), qq in walk.items():
        if teamof.get(pl) != ab or pl == outpl: continue
        if not (t0 < gt and (gt - t0).total_seconds() < 30*3600): continue
        pre = [x for x in qq if x[0] < t0]
        post = [x for x in qq if t0 <= x[0] < gt]
        if not pre or not post: continue
        # the line has NOT moved yet at the first post-flag capture = the book is late
        if abs(post[0][1] - pre[-1][1]) > 0.01: continue
        key = (pl, mk, gt)
        if key in usedkey: continue
        usedkey.add(key)
        now = pgrow.get((pl, gt))
        if not now or mk not in now: continue
        ln, od = post[0][1], post[0][2]
        if now[mk] == ln: continue
        LAT.append(dict(pl=pl, mk=mk, gid=gof.get((ab, gt)), ln=ln, o_od=od,
                        o_won=now[mk] > ln, u_od=od, u_won=now[mk] < ln,
                        lag=(gt - t0).total_seconds()/3600))
print(f"  {len(LAT)} teammate quotes captured post-flag with the line still unmoved")
show(LAT, "teammate OVER at the stale (pre-news) line", "o", minn=40)
near = [r for r in LAT if r["lag"] < 12]
show(near, "  same, flag within 12h of tip (freshest news)", "o", minn=25)
if len(LAT) >= 40:
    ctl = [r for r in Q if r["mk"] in ("pts", "pr", "pra", "pa", "reb", "ast", "ra")]
    print(f"    control: all board overs run {roi(ctl,'o'):+.1f}%")
