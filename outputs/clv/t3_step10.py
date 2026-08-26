# TRACK 3 step 10: quadrant correlations + headline counts.
import pickle, os, sys, math, statistics, collections, random, csv
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = r"C:\Users\Axioo\wnba-line-capture"
rows = pickle.load(open(os.path.join(D, "outputs", "clv", "indep_rows.pkl"), "rb"))
sharp = pickle.load(open(os.path.join(D, "outputs", "clv", "sharp_rows.pkl"), "rb"))

def corr(xs, ys):
    mx, my = statistics.mean(xs), statistics.mean(ys)
    n = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    d = math.sqrt(sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys))
    return n / d if d else float("nan")

fams = collections.defaultdict(list)
for r in rows: fams[r["src"]].append(r)
pts = []
for k, v in fams.items():
    if len(v) < 20: continue
    lc = statistics.mean([r["ind_line"] for r in v])
    oc = statistics.mean([r["ind_odds"] for r in v if r["ind_odds"] is not None])
    ev = statistics.mean([r["ev_close"] for r in v if r["ev_close"] is not None])
    roi = statistics.mean([r["pnl"] for r in v])
    pts.append((k, lc, oc, ev, roi, len(v)))
print("=== ACROSS-FAMILY CORRELATION OF EACH CLV FLAVOUR WITH REALISED ROI (k=%d families, n>=20) ===" % len(pts))
print("  corr(independent LINE-CLV, ROI)   = %+.3f" % corr([p[1] for p in pts], [p[4] for p in pts]))
print("  corr(independent ODDS-CLV, ROI)   = %+.3f" % corr([p[2] for p in pts], [p[4] for p in pts]))
print("  corr(EV vs 1xbet vig-free close, ROI) = %+.3f" % corr([p[3] for p in pts], [p[4] for p in pts]))
sf = collections.defaultdict(list)
for r in sharp: sf[r["src"]].append(r)
sp = [(k, statistics.mean([x["ev_cls"] for x in v]), statistics.mean([x["pnl"] for x in v]), len(v))
      for k, v in sf.items() if len(v) >= 8]
print("  corr(SHARP odds-CLV vs Pinnacle close, ROI) = %+.3f  (k=%d families with >=8 sharp-referenced bets)" % (
    corr([p[1] for p in sp], [p[2] for p in sp]), len(sp)))
for p in sorted(sp, key=lambda x: -x[3]):
    print("     %-12s sharpCLV %+6.2f%%  ROI %+6.1f%%  n=%d" % (p[0], p[1] * 100, p[2] * 100, p[3]))

print("\n=== BET-LEVEL: does INDEPENDENT line-CLV predict pnl? (game-block permutation) ===")
for lo, hi, lbl in ((-99, -0.01, "line moved AGAINST us"), (-0.01, 0.01, "line unchanged"), (0.01, 99, "line moved TOWARD us")):
    v = [r for r in rows if lo < r["ind_line"] <= hi]
    if len(v) < 10: continue
    d = collections.defaultdict(list)
    for r in v: d[r["gid"]].append(r["pnl"])
    b = list(d.values()); ms = []
    for _ in range(4000):
        s = [random.choice(b) for _ in range(len(b))]; fl = [x for q in s for x in q]; ms.append(sum(fl) / len(fl))
    ms.sort()
    print("  %-24s n=%4d games=%3d  ROI %+6.1f%% [%+6.1f,%+6.1f]" % (
        lbl, len(v), len(b), statistics.mean([r["pnl"] for r in v]) * 100, ms[100] * 100, ms[3900] * 100))

print("\n=== HEADLINE COUNTS FOR TRACK 3 ===")
gset = set(r["gid"] for r in rows) | set(r["gid"] for r in sharp)
print("  player-prop CLV rows analysed: %d over %d independent games" % (len(rows), len(set(r["gid"] for r in rows))))
print("  of which with a Pinnacle sharp reference: %d over %d games (pts only)" % (len(sharp), len(set(r["gid"] for r in sharp))))
GL = set()
for r in csv.DictReader(open(os.path.join(D, "gamelines.csv"), encoding="utf-8")): GL.add(r["matchup_id"])
print("  pre-game GAME-market matchups in gamelines.csv: %d ; linked to a final score with usable series: 111 spread / 114 total" % len(GL))
print("  union of independent games touched by track 3: %d (props) " % len(gset))
