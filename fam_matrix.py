# fam_matrix.py - THE OTHER MODEL FAMILIES.
# Every src family, both directions (as-emitted and FADED at the real opposite quote),
# each Model S gate applied in turn, plus tier and ev. Grid declared up front, noise
# ceiling computed by GAME-BLOCK permutation BEFORE the real table is printed.
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

MK3 = ("pra", "pr", "pts")
BETS = []; drop = collections.Counter()
for r in G:
    pl = (r["player"] or "").lower(); d = nd(r["date"]); mk = r["market"]; sd = r["side"]
    ln = f(r["line"]); od = f(r["odds"]); act = f(r["actual"])
    if ln is None or od is None or act is None: drop["badrow"] += 1; continue
    tps = dt2tip.get((pl, d))
    if not tps: drop["no_box"] += 1; continue
    gt = tps[0]
    if act == ln: drop["push"] += 1; continue
    rows = li.get((d, pl, mk, sd), []); ex = [z for z in rows if f(z[1]["line"]) == ln]
    sr = ex or rows
    T = sr[0][0] if sr else gt - datetime.timedelta(hours=12)
    tier = r.get("tier") or (sr[0][1]["tier"] if sr else "")
    ev = f(sr[0][1]["ev"]) if sr else None
    opp = "Under" if sd == "Over" else "Over"
    cand = [z for z in bi.get((pl, mk, opp, ln), []) if z[0] <= gt and (gt - z[0]).total_seconds() <= 60 * 3600]
    oppod = min(cand, key=lambda z: abs((z[0] - T).total_seconds()))[1] if cand else None
    over_won = act > ln
    won = over_won if sd == "Over" else (not over_won)
    prev = prevline.get((pl, mk, gt))
    mv = None if prev is None else ln - prev
    tm = pgrow[(pl, gt)]["tm"]
    o2 = OPP.get((tm, gt))
    gg = GM.get((o2[0], tuple(sorted((tm, o2[1])))), {}) if o2 else {}
    tot = gg.get("tot", (None, None))[1]
    pr_ = [x for x in hist.get(pl, []) if x["tip"] < gt and x["tm"] == tm]
    vol = (statistics.pstdev([x[mk] for x in pr_]) / ln) if (len(pr_) >= 5 and ln) else None
    BETS.append(dict(date=d, pl=pl, mk=mk, sd=sd, ln=ln, od=od, oppod=oppod, gt=gt,
                     won=won, over_won=over_won, src=r["src"], tier=tier, ev=ev,
                     mv=mv, tot=tot, vol=vol))

print("graded rows %d  usable %d  dropped %s" % (len(G), len(BETS), dict(drop)))
TWO = [b for b in BETS if b["oppod"] is not None]
print("two-sided (real opposite quote at the SAME line) %d = %.0f%% coverage"
      % (len(TWO), 100.0 * len(TWO) / len(BETS)))
print("  coverage rate by family:")
for s in sorted(set(b["src"] for b in BETS)):
    a = [b for b in BETS if b["src"] == s]; h = [b for b in a if b["oppod"] is not None]
    print("    %-11s %4d/%-4d = %3.0f%%" % (s, len(h), len(a), 100.0 * len(h) / len(a)))
mg = [1 / b["od"] + 1 / b["oppod"] - 1 for b in TWO]
print("  median two-sided board margin %.1f%%" % (100 * statistics.median(mg)))
print("  feature presence on TWO: %s" %
      {k: sum(1 for b in TWO if b[k] is not None) for k in ("mv", "tot", "vol", "ev")})

vv = sorted(b["vol"] for b in TWO if b["vol"] is not None)
VOL_HI = vv[int(len(vv) * 2 / 3)] if vv else None
tt = sorted(b["tot"] for b in TWO if b["tot"] is not None)
TOT_MED = tt[len(tt) // 2] if tt else None
evs = sorted(b["ev"] for b in TWO if b["ev"] is not None)
EV_T1, EV_T2 = (evs[len(evs) // 3], evs[2 * len(evs) // 3]) if evs else (None, None)
print("  vol top-tercile cut sd/line >= %.3f   total median %s   ev terciles %.3f / %.3f"
      % (VOL_HI, TOT_MED, EV_T1, EV_T2))


def g_none(b): return True
def g_mk3(b): return b["mk"] in MK3
def g_notraise(b): return b["mv"] is not None and b["mv"] < 0.5
def g_notcut(b): return b["mv"] is not None and b["mv"] > -0.5
def g_vol(b): return b["vol"] is not None and b["vol"] < VOL_HI
def g_tot(b):
    if b["tot"] is None: return False
    return b["tot"] >= TOT_MED if b["sd"] == "Over" else b["tot"] < TOT_MED


GATES = [("none", g_none), ("mk in pra/pr/pts", g_mk3), ("not RAISED >=.5", g_notraise),
         ("not CUT >=.5", g_notcut), ("1 pos/player (best price)", None),
         ("vol cut (drop top 3rd)", g_vol), ("total cut", g_tot)]


def one_per_player(rows, fade):
    best = {}
    for b in rows:
        k = (b["date"], b["pl"])
        price = b["oppod"] if fade else b["od"]
        if k not in best or price > (best[k]["oppod"] if fade else best[k]["od"]): best[k] = b
    return list(best.values())


FAMS = sorted(set(b["src"] for b in TWO))
TIERS = ("THIN", "SOLID", "STRONG", "CASC")
CELLS = []
for fam in FAMS:
    for dirn in ("EMIT", "FADE"):
        for gname, gf in GATES:
            CELLS.append((fam + " " + dirn + " | " + gname, fam, dirn, gf, gf is None))
        for t in TIERS:
            CELLS.append((fam + " " + dirn + " | tier " + t, fam, dirn,
                          (lambda b, t=t: b["tier"] == t), False))
        for i, (lo, hi) in enumerate(((-9, EV_T1), (EV_T1, EV_T2), (EV_T2, 9))):
            CELLS.append((fam + " " + dirn + " | ev T%d" % (i + 1), fam, dirn,
                          (lambda b, lo=lo, hi=hi: b["ev"] is not None and lo <= b["ev"] < hi), False))
MINN = 40
print("\nDECLARED GRID: %d families x 2 directions x (%d gates + %d tiers + 3 ev terciles) = %d cells, min n=%d"
      % (len(FAMS), len(GATES), len(TIERS), len(CELLS), MINN))


def cell_rows(fam, dirn, sel, onepos):
    rows = [b for b in TWO if b["src"] == fam]
    return one_per_player(rows, dirn == "FADE") if onepos else [b for b in rows if sel(b)]


def roi(rows, dirn, lab):
    if len(rows) < MINN: return None
    p = 0.0
    for b in rows:
        w = lab[id(b)]
        if dirn == "EMIT": p += (b["od"] - 1) if w else -1.0
        else: p += -1.0 if w else (b["oppod"] - 1)
    return p / len(rows)


PRE = [(nm, cell_rows(fam, dirn, sel, op), dirn) for nm, fam, dirn, sel, op in CELLS]
live = [(nm, rows, dirn) for nm, rows, dirn in PRE if len(rows) >= MINN]
print("  cells reaching n>=%d: %d" % (MINN, len(live)))

gm_blocks = collections.defaultdict(list)
for b in TWO: gm_blocks[b["gt"]].append(b)
blocks = [v for k, v in sorted(gm_blocks.items())]
flat_all = [b for blk in blocks for b in blk]


def block_perm_labels():
    bl = list(blocks); random.shuffle(bl)
    stream = [b["won"] for blk in bl for b in blk]
    return {id(b): w for b, w in zip(flat_all, stream)}


side_blocks = {}
side_flat = {}
for s in ("Over", "Under"):
    bs = [[b for b in blk if b["sd"] == s] for blk in blocks]
    bs = [x for x in bs if x]
    side_blocks[s] = bs
    side_flat[s] = [b for blk in bs for b in blk]


def sided_block_perm():
    lab = {}
    for s in ("Over", "Under"):
        sh = list(side_blocks[s]); random.shuffle(sh)
        stream = [b["won"] for blk in sh for b in blk]
        lab.update({id(b): w for b, w in zip(side_flat[s], stream)})
    return lab


T = 2000


def ceiling(gen):
    sims = []
    for _ in range(T):
        lab = gen()
        best = -9.0
        for nm, rows, dirn in live:
            v = roi(rows, dirn, lab)
            if v is not None and v > best: best = v
        sims.append(best)
    sims.sort(); return sims


s1 = ceiling(block_perm_labels)
s2 = ceiling(sided_block_perm)
C1, C2 = s1[int(T * 0.95)], s2[int(T * 0.95)]
CEIL = max(C1, C2)
print("\n" + "=" * 104)
print("  NOISE CEILING, best-of-grid under the null (%d reps, GAME-BLOCK permutation)" % T)
print("    unstratified    median %+5.1f%%   p95 %+5.1f%%   max %+5.1f%%" % (100 * s1[T // 2], 100 * C1, 100 * s1[-1]))
print("    side-stratified median %+5.1f%%   p95 %+5.1f%%   max %+5.1f%%" % (100 * s2[T // 2], 100 * C2, 100 * s2[-1]))
print("    ===> CEILING = p95 = %+.1f%% ROI. A cell under this is NOT a finding." % (100 * CEIL))
print("=" * 104)

real = {id(b): b["won"] for b in TWO}
res = []
for nm, rows, dirn in live:
    v = roi(rows, dirn, real)
    wins = sum(1 for b in rows if real[id(b)]) if dirn == "EMIT" else sum(1 for b in rows if not real[id(b)])
    pn = []
    for b in rows:
        w = real[id(b)]
        pn.append(((b["od"] - 1) if w else -1.0) if dirn == "EMIT" else (-1.0 if w else (b["oppod"] - 1)))
    se = statistics.pstdev(pn) / math.sqrt(len(pn))
    res.append((v, nm, len(rows), wins / len(rows), se, dirn, rows))
res.sort(key=lambda z: -z[0])
# per-cell p-value against the same null
pv = {}
for nm, rows, dirn in live: pv[nm] = 0
for _ in range(T):
    lab = sided_block_perm()
    for nm, rows, dirn in live:
        v = roi(rows, dirn, lab)
        rv = roi(rows, dirn, real)
        if v is not None and v >= rv: pv[nm] += 1
print("\n  ALL %d LIVE CELLS, sorted by ROI  (CI = 95%% normal on per-bet pnl; p = own-cell block-perm)" % len(res))
for v, nm, n, wr, se, dirn, rows in res:
    flag = "  <== CLEARS CEILING" if v >= CEIL else ""
    print("  %-48s n=%-4d win %4.1f%%  ROI %+6.1f%%  CI[%+6.1f,%+6.1f]  p=%.3f%s"
          % (nm, n, 100 * wr, 100 * v, 100 * (v - 1.96 * se), 100 * (v + 1.96 * se), pv[nm] / T, flag))
clears = [nm for v, nm, n, wr, se, d, rw in res if v >= CEIL]
print("\n  CELLS CLEARING THE CEILING: %s" % (clears if clears else "NONE"))

lo, hi = min(b["date"] for b in TWO), max(b["date"] for b in TWO)
bb = [r for r in B if lo <= r["date"] <= hi]


def broi(rows, sside):
    if not rows: return None, 0
    p = sum(((r["over_od"] - 1) if r["over_won"] else -1.0) if sside == "Over"
            else (-1.0 if r["over_won"] else (r["under_od"] - 1)) for r in rows)
    return p / len(rows), len(rows)


print("\n" + "=" * 104)
print("  BASE-RATE CONTROL: blind board ROI over the same window (is a 'fade' just the over base rate?)")
for sside in ("Over", "Under"):
    v, n = broi(bb, sside); print("    ALL markets  blind %-5s n=%-5d ROI %+5.1f%%" % (sside, n, 100 * v))
for mk in ("pts", "pra", "pr", "pa", "reb", "ast", "ra"):
    s = [r for r in bb if r["mk"] == mk]
    if len(s) < 80: continue
    vo, _ = broi(s, "Over"); vu, _ = broi(s, "Under")
    print("    %-4s n=%-5d blind Over %+5.1f%%  blind Under %+5.1f%%" % (mk, len(s), 100 * vo, 100 * vu))
print("=" * 104)

print("\n  FAMILY HEADLINE, as-emitted at the ping price")
print("  %-11s %6s %8s   %11s %9s %9s" % ("family", "ALL n", "ROI", "two-sided n", "EMIT ROI", "FADE ROI"))
for s in sorted(set(b["src"] for b in BETS)):
    a = [b for b in BETS if b["src"] == s]
    pa = sum((b["od"] - 1) if b["won"] else -1.0 for b in a) / len(a)
    t2 = [b for b in a if b["oppod"] is not None]
    if t2:
        pe = sum((b["od"] - 1) if b["won"] else -1.0 for b in t2) / len(t2)
        pf = sum(-1.0 if b["won"] else (b["oppod"] - 1) for b in t2) / len(t2)
        print("  %-11s %6d %+7.1f%%   %11d %+8.1f%% %+8.1f%%" % (s, len(a), 100 * pa, len(t2), 100 * pe, 100 * pf))
    else:
        print("  %-11s %6d %+7.1f%%   %11s" % (s, len(a), 100 * pa, "-"))

print("\n  TIER AND EV MONOTONICITY (as-emitted, two-sided sample). non-monotonic = noise")
for s in FAMS:
    a = [b for b in TWO if b["src"] == s]
    if len(a) < 40: continue
    line = []
    for t in TIERS:
        g = [b for b in a if b["tier"] == t]
        if len(g) >= 15:
            r_ = sum((b["od"] - 1) if b["won"] else -1.0 for b in g) / len(g)
            line.append("%s n=%d %+.1f%%" % (t, len(g), 100 * r_))
    ev = [b for b in a if b["ev"] is not None]
    evl = []
    if len(ev) >= 45:
        q = sorted(ev, key=lambda b: b["ev"]); k = len(q) // 3
        for i, g in enumerate((q[:k], q[k:2 * k], q[2 * k:])):
            r_ = sum((b["od"] - 1) if b["won"] else -1.0 for b in g) / len(g)
            evl.append("T%d n=%d %+.1f%%" % (i + 1, len(g), 100 * r_))
    print("    %-11s tier: %s" % (s, " | ".join(line) if line else "no variation"))
    print("    %-11s ev  : %s" % ("", " | ".join(evl) if evl else "n/a"))


def spearman(xs, ys):
    n = len(xs)
    if n < 10: return None
    def rk(v):
        s = sorted(range(n), key=lambda i: v[i]); r = [0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[s[j + 1]] == v[s[i]]: j += 1
            for k2 in range(i, j + 1): r[s[k2]] = (i + j) / 2 + 1
            i = j + 1
        return r
    a, b2 = rk(xs), rk(ys)
    ma, mb = sum(a) / n, sum(b2) / n
    num = sum((a[i] - ma) * (b2[i] - mb) for i in range(n))
    den = math.sqrt(sum((a[i] - ma) ** 2 for i in range(n)) * sum((b2[i] - mb) ** 2 for i in range(n)))
    return num / den if den else None


print("\n  SPEARMAN rho(ev, realised pnl) per family, as-emitted")
for s in FAMS:
    a = [b for b in TWO if b["src"] == s and b["ev"] is not None]
    if len(a) < 40: continue
    xs = [b["ev"] for b in a]; ys = [((b["od"] - 1) if b["won"] else -1.0) for b in a]
    rh = spearman(xs, ys)
    z = rh * math.sqrt(len(a) - 1) if rh is not None else 0
    print("    %-11s n=%-4d rho %+.3f  z %+.2f" % (s, len(a), rh, z))
