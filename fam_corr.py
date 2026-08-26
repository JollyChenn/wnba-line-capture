# fam_corr.py - measured correlations worth recording from the family sweep.
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
    ev = f(sr[0][1]["ev"]) if sr else None
    opp = "Under" if sd == "Over" else "Over"
    cand = [z for z in bi.get((pl, mk, opp, ln), []) if z[0] <= gt and (gt - z[0]).total_seconds() <= 60 * 3600]
    oppod = min(cand, key=lambda z: abs((z[0] - T).total_seconds()))[1] if cand else None
    prev = prevline.get((pl, mk, gt))
    tm = pgrow[(pl, gt)]["tm"]; o2 = OPP.get((tm, gt))
    gg = GM.get((o2[0], tuple(sorted((tm, o2[1])))), {}) if o2 else {}
    BETS.append(dict(date=d, pl=pl, mk=mk, sd=sd, ln=ln, od=od, oppod=oppod, act=act, gt=gt,
                     over_won=act > ln, won=(act > ln) if sd == "Over" else (act < ln),
                     src=r["src"], mv=(None if prev is None else ln - prev),
                     tot=gg.get("tot", (None, None))[1], ev=ev, tier=r.get("tier")))
def spearman(xs, ys):
    n = len(xs)
    def rk(v):
        s = sorted(range(n), key=lambda i: v[i]); r = [0.0] * n; i = 0
        while i < n:
            j = i
            while j + 1 < n and v[s[j + 1]] == v[s[i]]: j += 1
            for k in range(i, j + 1): r[s[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    a, b = rk(xs), rk(ys); ma = sum(a) / n; mb = sum(b) / n
    num = sum((a[i] - ma) * (b[i] - mb) for i in range(n))
    den = math.sqrt(sum((a[i] - ma) ** 2 for i in range(n)) * sum((b[i] - mb) ** 2 for i in range(n)))
    return num / den if den else 0.0
print("MEASURED CORRELATIONS")
for fam in ("newunder", "overshoot", "flip_paper", "cascade"):
    a = [b for b in BETS if b["src"] == fam]
    # ev vs pnl
    g = [b for b in a if b["ev"] is not None]
    if len(g) >= 40:
        rh = spearman([b["ev"] for b in g], [((b["od"] - 1) if b["won"] else -1.0) for b in g])
        print("  %-11s rho(engine ev, realised pnl)          %+.3f  n=%-4d z=%+.2f" % (fam, rh, len(g), rh * math.sqrt(len(g) - 1)))
    # game total vs over margin (mechanism, no prices)
    g = [b for b in a if b["tot"] is not None]
    if len(g) >= 40:
        rh = spearman([b["tot"] for b in g], [(b["act"] - b["ln"]) / b["ln"] for b in g])
        print("  %-11s rho(Pinnacle game total, over-margin) %+.3f  n=%-4d z=%+.2f" % (fam, rh, len(g), rh * math.sqrt(len(g) - 1)))
    # line move vs over margin
    g = [b for b in a if b["mv"] is not None]
    if len(g) >= 40:
        rh = spearman([b["mv"] for b in g], [(b["act"] - b["ln"]) / b["ln"] for b in g])
        print("  %-11s rho(line move vs prev, over-margin)   %+.3f  n=%-4d z=%+.2f" % (fam, rh, len(g), rh * math.sqrt(len(g) - 1)))
# board-wide for reference
g = [r for r in B if r["linemv"] is not None]
rh = spearman([r["linemv"] for r in g], [1.0 if r["over_won"] else 0.0 for r in g])
print("  FULL BOARD  rho(line move, over hit)              %+.3f  n=%-5d z=%+.2f" % (rh, len(g), rh * math.sqrt(len(g) - 1)))
# tot coverage
print("\n  Pinnacle-total coverage on graded bets: %d of %d = %.0f%%"
      % (sum(1 for b in BETS if b["tot"] is not None), len(BETS),
         100 * sum(1 for b in BETS if b["tot"] is not None) / len(BETS)))
print("  newunder total coverage: %d of %d"
      % (sum(1 for b in BETS if b["src"] == "newunder" and b["tot"] is not None),
         sum(1 for b in BETS if b["src"] == "newunder")))
print("\n  market composition per family:")
for fam in sorted(set(b["src"] for b in BETS)):
    print("    %-11s %s" % (fam, dict(collections.Counter(b["mk"] for b in BETS if b["src"] == fam))))
