# CONFOUND LENS on the claim: "within-player demeaned lag-1 autocorr of the points residual
# is +0.191 -> big scoring games PERSIST".
# Suspected confounds: (a) the SHARED med_G baseline is NOT removed by within-player demeaning
# (it only removes med_G's player MEAN, not its within-player variance, which enters the
# covariance with a + sign); (b) minutes/role persistence = volume proxy; (c) slow role drift
# (a trailing median lags a drifting level) -> would show as NO decay across lags.
import os, sys, csv, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hlib; ROOT = hlib.boot(globals())
random.seed(20260826)

def slope_corr(x, y):
    n = len(x); mx = sum(x)/n; my = sum(y)/n
    sxy = sum((a-mx)*(b-my) for a, b in zip(x, y))
    sxx = sum((a-mx)**2 for a in x); syy = sum((b-my)**2 for b in y)
    if sxx <= 0 or syy <= 0: return 0.0, 0.0
    return sxy/sxx, sxy/math.sqrt(sxx*syy)

def demean_pairs(pairs, minT=5):
    xs, ys, keys = [], [], []
    for p, v in pairs.items():
        if len(v) < minT: continue
        mx = sum(a for a, b in v)/len(v); my = sum(b for a, b in v)/len(v)
        for a, b in v:
            xs.append(a-mx); ys.append(b-my); keys.append(p)
    return xs, ys, keys

def blockperm(pairs, minT=5, B=2000):
    xs, ys, keys = demean_pairs(pairs, minT)
    b_, r_ = slope_corr(xs, ys)
    idx = collections.defaultdict(list)
    for i, k in enumerate(keys): idx[k].append(i)
    cnt = 0
    for _ in range(B):
        y2 = list(ys)
        for k, ii in idx.items():
            v = [ys[i] for i in ii]; random.shuffle(v)
            for i, val in zip(ii, v): y2[i] = val
        if abs(slope_corr(xs, y2)[1]) >= abs(r_): cnt += 1
    return b_, r_, len(xs), len(idx), (cnt+1)/(B+1)

def boot_ci(pairs, minT=5, B=800):
    ps = [p for p, v in pairs.items() if len(v) >= minT]
    out = []
    for _ in range(B):
        samp = {}
        for j in range(len(ps)):
            p = random.choice(ps); samp[(p, j)] = pairs[p]
        xs, ys, _ = demean_pairs(samp, minT)
        if len(xs) > 20: out.append(slope_corr(xs, ys)[1])
    out.sort()
    return out[int(.025*len(out))], out[int(.975*len(out))]

H1 = {}
for r in load("outputs/hyp/h1_all.csv"):
    gid = r["game_id"]
    if gid not in gmeta: continue
    H1[(r["player"], gmeta[gid][1])] = dict(h1=f(r["h1"]), h2=f(r["h2"]), pts=f(r["pts"]))
Q = {}
for (pl, mk, gt), sd in side.items():
    if mk != "pts" or "Over" not in sd or "Under" not in sd: continue
    if sd["Over"][1] != sd["Under"][1]: continue
    Q[(pl, gt)] = sd["Over"][1]

def trail(pl, gt, k=10, mk="pts"):
    p = [x for x in hist.get(pl, []) if x["tip"] < gt and x["tm"] == teamof.get(pl)][-k:]
    return statistics.median(x[mk] for x in p) if len(p) >= 5 else None

M = []
for (pl, gt), h in sorted(H1.items(), key=lambda k: (k[0][0], k[0][1])):
    now = pgrow.get((pl, gt))
    if not now or now["min"] < 8: continue
    m_g = trail(pl, gt)
    if m_g is None: continue
    fut = [x for x in hist.get(pl, []) if x["tip"] > gt]
    if not fut: continue
    nx = fut[0]
    if nx["min"] < 8: continue
    m_n = trail(pl, nx["tip"])
    M.append(dict(pl=pl, gt=gt, pts=now["pts"], mn=now["min"], med_g=m_g,
                  npts=nx["pts"], nmin=nx["min"], med_n=m_n,
                  resid=nx["pts"]-m_g, resid_g=now["pts"]-m_g))
print("panel n=%d players=%d" % (len(M), len(set(r["pl"] for r in M))))

def pk(fx, fy, rows=M):
    d = collections.defaultdict(list)
    for r in rows:
        try: a, b = fx(r), fy(r)
        except Exception: continue
        if a is None or b is None: continue
        d[r["pl"]].append((a, b))
    return d

print("")
print("="*78)
print("STEP 0  REPLICATE THE CLAIM  (x=pts_G-med_G , y=pts_G1-med_G  <- SAME med_G)")
print("="*78)
P0 = pk(lambda r: r["resid_g"], lambda r: r["resid"])
b, r, n, npl, p = blockperm(P0)
lo, hi = boot_ci(P0)
print("  slope %+.4f  corr %+.4f  n=%d  players=%d  block p=%.4f  CI[%.3f,%.3f]" % (b, r, n, npl, p, lo, hi))
b2, r2 = slope_corr([x["resid_g"] for x in M], [x["resid"] for x in M])
print("  (undemeaned for reference: slope %+.4f corr %+.4f)" % (b2, r2))

print("")
print("="*78)
print("CONFOUND A  THE SHARED med_G IS STILL IN THERE AFTER DEMEANING")
print("="*78)
dd = collections.defaultdict(list)
for r in M: dd[r["pl"]].append(r)
A = []
for p_, v in dd.items():
    if len(v) < 5: continue
    ma = sum(x["pts"] for x in v)/len(v); mb = sum(x["npts"] for x in v)/len(v)
    mm = sum(x["med_g"] for x in v)/len(v)
    for x in v: A.append((x["pts"]-ma, x["npts"]-mb, x["med_g"]-mm))
n = len(A)
cov = lambda i, j: sum(a[i]*a[j] for a in A)/n
c_pp, c_pm, c_nm, v_m = cov(0,1), cov(0,2), cov(1,2), cov(2,2)
tot = c_pp - c_pm - c_nm + v_m
print("  Cov(resid_g,resid) decomposition, all within-player demeaned:")
print("    +Cov(pts_G, pts_G1)   %+8.3f   <- the ONLY real persistence term" % c_pp)
print("    -Cov(pts_G, med_G)    %+8.3f" % (-c_pm))
print("    -Cov(pts_G1, med_G)   %+8.3f" % (-c_nm))
print("    +Var(med_G)           %+8.3f   <- ARTIFACT: identical med_G on both sides" % v_m)
print("    = total               %+8.3f   (share from +Var(med_G): %.1f%%)" % (tot, 100*v_m/tot))

print("")
print("  -> CLEAN v1: each game keeps its OWN pre-game trailing median as baseline")
P1 = pk(lambda r: r["resid_g"], lambda r: (r["npts"]-r["med_n"]) if r["med_n"] is not None else None)
b, r, n, npl, p = blockperm(P1)
lo, hi = boot_ci(P1)
print("     x=pts_G-med_G , y=pts_G1-med_G1 :  corr %+.4f  n=%d players=%d p=%.4f CI[%.3f,%.3f]"
      % (r, n, npl, p, lo, hi))

print("")
print("  -> CLEAN v2 (cleanest): NO baseline. player fixed effect only = the true lag-1 autocorr")
P2 = pk(lambda r: r["pts"], lambda r: r["npts"])
b, r, n, npl, p = blockperm(P2)
lo, hi = boot_ci(P2)
print("     x=pts_G , y=pts_G1 (both within-player demeaned): corr %+.4f  n=%d players=%d p=%.4f CI[%.3f,%.3f]"
      % (r, n, npl, p, lo, hi))
RAW = r

print("")
print("="*78)
print("CONFOUND B  IS IT JUST MINUTES / ROLE (volume proxy)?")
print("="*78)
Pm = pk(lambda r: r["mn"], lambda r: r["nmin"])
b, rm_, n, npl, p = blockperm(Pm)
print("  lag-1 autocorr of MINUTES itself      : corr %+.4f  n=%d p=%.4f" % (rm_, n, p))
Pr = pk(lambda r: (r["pts"]/r["mn"]) if r["mn"] else None, lambda r: (r["npts"]/r["nmin"]) if r["nmin"] else None)
b, r2, n, npl, p = blockperm(Pr)
lo, hi = boot_ci(Pr)
print("  lag-1 autocorr of PTS PER MINUTE      : corr %+.4f  n=%d p=%.4f CI[%.3f,%.3f]" % (r2, n, p, lo, hi))
mx, my, kk = demean_pairs(pk(lambda r: r["mn"], lambda r: r["pts"]))
sl_g = slope_corr(mx, my)[0]
mx2, my2, _ = demean_pairs(pk(lambda r: r["nmin"], lambda r: r["npts"]))
sl_n = slope_corr(mx2, my2)[0]
print("  within-player pts~min slope: G %.3f pts/min, G+1 %.3f pts/min" % (sl_g, sl_n))
Pp = pk(lambda r: r["pts"] - sl_g*r["mn"], lambda r: r["npts"] - sl_n*r["nmin"])
b, r3, n, npl, p = blockperm(Pp)
lo, hi = boot_ci(Pp)
print("  lag-1 autocorr of pts | minutes partialled out: corr %+.4f n=%d p=%.4f CI[%.3f,%.3f]" % (r3, n, p, lo, hi))
if RAW: print("  -> minutes explain %.0f%% of the raw pts persistence (%.4f -> %.4f)" % (100*(1-r3/RAW), RAW, r3))

print("")
print("="*78)
print("CONFOUND C  DECAY PROFILE: true carryover decays; a slow role/health LEVEL does not")
print("="*78)
seq = {}
for pl, v in hist.items():
    s = sorted([x for x in v if x["min"] >= 8], key=lambda x: x["tip"])
    if len(s) >= 8: seq[pl] = s
print("  full box panel: %d players, %d player-games (no halves/quote restriction)" % (
      len(seq), sum(len(v) for v in seq.values())))
print("  %-5s %10s %10s %10s %8s" % ("lag", "corr(pts)", "corr(min)", "corr(p/m)", "n"))
for L in (1, 2, 3, 4, 5, 6, 8, 10):
    dp = collections.defaultdict(list); dm = collections.defaultdict(list); drr = collections.defaultdict(list)
    for pl, s in seq.items():
        for i in range(len(s)-L):
            dp[pl].append((s[i]["pts"], s[i+L]["pts"]))
            dm[pl].append((s[i]["min"], s[i+L]["min"]))
            if s[i]["min"] and s[i+L]["min"]:
                drr[pl].append((s[i]["pts"]/s[i]["min"], s[i+L]["pts"]/s[i+L]["min"]))
    xs, ys, _ = demean_pairs(dp); rp = slope_corr(xs, ys)[1]
    xs2, ys2, _ = demean_pairs(dm); rmn = slope_corr(xs2, ys2)[1]
    xs3, ys3, _ = demean_pairs(drr); rr = slope_corr(xs3, ys3)[1]
    print("  %-5d %+10.4f %+10.4f %+10.4f %8d" % (L, rp, rmn, rr, len(xs)))

print("")
print("="*78)
print("CONFOUND D  SELECTION: unfiltered full-season panel")
print("="*78)
dp = collections.defaultdict(list)
for pl, s in seq.items():
    for i in range(len(s)-1): dp[pl].append((s[i]["pts"], s[i+1]["pts"]))
b, r, n, npl, p = blockperm(dp)
lo, hi = boot_ci(dp)
print("  UNFILTERED lag-1 pts autocorr   : corr %+.4f n=%d players=%d p=%.4f CI[%.3f,%.3f]"
      % (r, n, npl, p, lo, hi))
dr = collections.defaultdict(list)
for pl, s in seq.items():
    for i in range(len(s)-1):
        if s[i]["min"] and s[i+1]["min"]:
            dr[pl].append((s[i]["pts"]/s[i]["min"], s[i+1]["pts"]/s[i+1]["min"]))
b, r, n, npl, p = blockperm(dr)
lo, hi = boot_ci(dr)
print("  UNFILTERED lag-1 PTS/MIN autocorr: corr %+.4f n=%d players=%d p=%.4f CI[%.3f,%.3f]"
      % (r, n, npl, p, lo, hi))
