# TRACK 3 step 6: is "beat the close" independent evidence, or just ROI restated?
#  - proper parametric null for the beat-the-close delta
#  - Pinnacle (SHARP) close for Model S, not just 1xbet's own close
#  - how much does the 1xbet prop market actually move at all?
import csv, os, sys, math, statistics, collections, random, datetime
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = r"C:\Users\Axioo\wnba-line-capture"

def ts(s):
    s = (s or "").replace("Z", "+00:00")
    try: return datetime.datetime.fromisoformat(s)
    except Exception: return None

GM = list(csv.DictReader(open(os.path.join(D, "data", "games_2026.csv"), encoding="utf-8")))
tipof = {g["game_id"]: ts(g["tip"]) for g in GM}; dateof = {g["game_id"]: g["date"] for g in GM}
pl_game = {}
for r in csv.DictReader(open(os.path.join(D, "data", "box_2026.csv"), encoding="utf-8")):
    if r["game_id"] in dateof: pl_game[(r["player"].lower(), dateof[r["game_id"]])] = r["game_id"]

Q = collections.defaultdict(list)
for r in csv.DictReader(open(os.path.join(D, "xbet_board.csv"), encoding="utf-8")):
    t = ts(r["captured_utc"])
    if not t: continue
    try: Q[(r["player"].lower(), r["market"])].append((t, float(r["line"]), r["side"], float(r["odds"])))
    except Exception: pass
for k in Q: Q[k].sort()
PS = collections.defaultdict(list)
for r in csv.DictReader(open(os.path.join(D, "pinn_snapshots.csv"), encoding="utf-8")):
    t = ts(r["captured_utc"])
    try: ln = float(r["pinn_line"]); fa = float(r["pinn_fair"])
    except Exception: continue
    if t: PS[(r["player"].lower(), r["market"], r["side"], ln)].append((t, fa))
for k in PS: PS[k].sort()

def vf(o, u, side):
    a, b = 1 / o, 1 / u; s = a + b
    return (a / s) if side == "Over" else (b / s)

def series(p, m, tip, line=None, hours=72):
    lo = tip - datetime.timedelta(hours=hours)
    q = [x for x in Q.get((p, m), ()) if lo < x[0] < tip and (line is None or abs(x[1] - line) < 1e-6)]
    snap = collections.defaultdict(dict)
    for t, ln, s, o in q: snap[(t, ln)][s] = o
    return sorted((k[0], k[1], v["Over"], v["Under"]) for k, v in snap.items() if "Over" in v and "Under" in v)

rows = []
for r in csv.DictReader(open(os.path.join(D, "shadow_forward.csv"), encoding="utf-8")):
    if r["config"] != "MODEL_S" or r["result"] not in ("WIN", "loss"): continue
    d = r["slate"].replace("-", ""); p = r["player"].lower(); m = r["market"]
    gid = pl_game.get((p, d))
    if not gid: continue
    tip = tipof[gid]; line = float(r["line"]); odds = float(r["odds"] or 0)
    S = series(p, m, tip, line)
    Sa = series(p, m, tip, None)
    if not S: continue
    ent_o, ent_u = S[0][2], S[0][3]
    cls_o, cls_u = S[-1][2], S[-1][3]
    pin = [x for x in PS.get((p, m, "Over", line), ()) if tip - datetime.timedelta(hours=72) < x[0] < tip]
    rows.append(dict(gid=gid, player=p, market=m, line=line, odds=odds, won=1 if r["result"] == "WIN" else 0,
                     p_ent=vf(ent_o, ent_u, "Over"), p_cls=vf(cls_o, cls_u, "Over"),
                     odds_ent=ent_o, odds_cls=cls_o,
                     cls_line=Sa[-1][1] if Sa else line,
                     pinn_fair_cls=(pin[-1][1] if pin else None),
                     pinn_lag=((tip - pin[-1][0]).total_seconds() / 3600 if pin else None)))

print("Model S rows with a 1xbet two-sided series at our line: %d  games=%d  markets=%s" % (
    len(rows), len(set(r["gid"] for r in rows)), collections.Counter(r["market"] for r in rows)))

def bboot(byblock, nb=6000):
    b = list(byblock.values())
    if len(b) < 3: return (float("nan"),) * 3
    allv = [x for q in b for x in q]; ms = []
    for _ in range(nb):
        s = [random.choice(b) for _ in range(len(b))]
        fl = [x for q in s for x in q]; ms.append(sum(fl) / len(fl))
    ms.sort(); return statistics.mean(allv), ms[int(.025 * nb)], ms[int(.975 * nb)]

print("\n=== HOW MUCH DOES THE 1XBET PROP MARKET MOVE AT ALL? (Model S population) ===")
dl = [r["cls_line"] - r["line"] for r in rows]
do = [r["odds_cls"] / r["odds_ent"] - 1 for r in rows]
dp = [r["p_cls"] - r["p_ent"] for r in rows]
print("  line   open->close: unchanged %.0f%%  mean %+.3f pts  |move|>=0.5 in %.0f%%" % (
    sum(1 for x in dl if abs(x) < 1e-6) / len(dl) * 100, statistics.mean(dl), sum(1 for x in dl if abs(x) >= .5) / len(dl) * 100))
print("  OVER price open->close at our line: unchanged %.0f%%  mean %+.2f%%" % (
    sum(1 for x in do if abs(x) < 1e-9) / len(do) * 100, statistics.mean(do) * 100))
print("  vig-free P(over) at our line drifted mean %+.3f pp; |drift|>1pp in %.0f%% of bets" % (
    statistics.mean(dp) * 100, sum(1 for x in dp if abs(x) > .01) / len(dp) * 100))
print("  => a near-static market: 'closing line value' vs 1xbet is measuring almost nothing.")

print("\n=== BEAT-THE-CLOSE, PROPER NULLS ===")
for lbl, key in (("1xbet OPEN  vig-free P(over) at our line", "p_ent"),
                 ("1xbet CLOSE vig-free P(over) at our line", "p_cls")):
    d = {}
    for r in rows: d.setdefault(r["gid"], []).append(r["won"] - r[key])
    m, lo, hi = bboot(d)
    # parametric null: won_i ~ Bernoulli(p_i)
    NB = 20000; cnt = 0
    ps = [r[key] for r in rows]
    for _ in range(NB):
        s = sum((1 if random.random() < p else 0) - p for p in ps) / len(ps)
        if s >= m: cnt += 1
    print("  vs %s:  delta %+5.1f pp  block-CI [%+5.1f,%+5.1f]  Bernoulli-null p=%.4f  implied %.1f%%" % (
        lbl, m * 100, lo * 100, hi * 100, (cnt + 1) / (NB + 1), statistics.mean(ps) * 100))

print("\n  ARITHMETIC CHECK -- is the delta independent of the ROI?")
hit = sum(r["won"] for r in rows) / len(rows)
avg_odds = statistics.mean([r["odds"] for r in rows if r["odds"]])
print("    hit-rate %.1f%% x mean odds %.3f - 1 = ROI %+.1f%%" % (hit * 100, avg_odds, hit * avg_odds * 100 - 100))
print("    mean vig-free P(over) at close %.1f%% ; mean 1xbet OVER decimal at close %.3f" % (
    statistics.mean([r["p_cls"] for r in rows]) * 100, statistics.mean([r["odds_cls"] for r in rows])))
print("    beat-close delta and ROI are the SAME statistic rescaled while the line does not move.")

print("\n=== SHARP CLOSE (Pinnacle vig-free fair) for Model S ===")
sp = [r for r in rows if r["pinn_fair_cls"]]
if sp:
    d = {}
    for r in sp: d.setdefault(r["gid"], []).append(r["won"] - 1 / r["pinn_fair_cls"])
    m, lo, hi = bboot(d)
    NB = 20000; cnt = 0; ps = [1 / r["pinn_fair_cls"] for r in sp]
    for _ in range(NB):
        s = sum((1 if random.random() < p else 0) - p for p in ps) / len(ps)
        if s >= m: cnt += 1
    e = {}
    for r in sp: e.setdefault(r["gid"], []).append(r["odds"] / r["pinn_fair_cls"] - 1)
    ev = bboot(e)
    pn = {}
    for r in sp: pn.setdefault(r["gid"], []).append((r["odds"] - 1) if r["won"] else -1.0)
    ro = bboot(pn)
    print("  n=%d  games=%d  markets=%s  sharp quote median %.2fh before tip" % (
        len(sp), len(d), collections.Counter(r["market"] for r in sp), statistics.median([r["pinn_lag"] for r in sp])))
    print("  PINNACLE close implies P(over) %.1f%% ; Model S actual %.1f%%" % (
        statistics.mean(ps) * 100, sum(r["won"] for r in sp) / len(sp) * 100))
    print("  BEAT-THE-SHARP-CLOSE delta %+5.1f pp  block-CI [%+5.1f,%+5.1f]  Bernoulli-null p=%.4f" % (
        m * 100, lo * 100, hi * 100, (cnt + 1) / (NB + 1)))
    print("  sharp odds-CLV (our price / Pinnacle fair - 1) %+5.2f%% [%+5.2f,%+5.2f]" % (ev[0] * 100, ev[1] * 100, ev[2] * 100))
    print("  realised ROI on this subset %+5.1f%% [%+5.1f,%+5.1f]" % (ro[0] * 100, ro[1] * 100, ro[2] * 100))
else:
    print("  NO Pinnacle coverage at Model S lines -- Model S is mostly pra/pr, Pinnacle sidecar is 97%% pts.")
