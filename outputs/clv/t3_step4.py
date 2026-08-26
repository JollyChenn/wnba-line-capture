# TRACK 3 step 4: sharp (Pinnacle) EV at ENTRY vs at CLOSE -- diagnostic and tradability.
# NOISE CEILING DECLARED AND COMPUTED BEFORE REAL RESULTS ARE PRINTED.
import csv, os, sys, math, statistics, collections, random, datetime, pickle
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = r"C:\Users\Axioo\wnba-line-capture"

def ts(s):
    s = (s or "").replace("Z", "+00:00")
    try: return datetime.datetime.fromisoformat(s)
    except Exception: return None

GM = list(csv.DictReader(open(os.path.join(D, "data", "games_2026.csv"), encoding="utf-8")))
tipof = {g["game_id"]: ts(g["tip"]) for g in GM}
dateof = {g["game_id"]: g["date"] for g in GM}
pl_game = {}
for r in csv.DictReader(open(os.path.join(D, "data", "box_2026.csv"), encoding="utf-8")):
    if r["game_id"] in dateof:
        pl_game[(r["player"].lower(), dateof[r["game_id"]])] = r["game_id"]

PS = collections.defaultdict(list)
for r in csv.DictReader(open(os.path.join(D, "pinn_snapshots.csv"), encoding="utf-8")):
    t = ts(r["captured_utc"])
    try:
        ln = float(r["pinn_line"]); fa = float(r["pinn_fair"])
    except Exception:
        continue
    if t: PS[(r["player"].lower(), r["market"], r["side"], ln)].append((t, fa))
for k in PS: PS[k].sort()
PSL = collections.defaultdict(list)
for k, v in PS.items(): PSL[(k[0], k[1], k[2])].extend([(t, k[3], f) for t, f in v])
for k in PSL: PSL[k].sort()

caps = collections.defaultdict(list)
for b in csv.DictReader(open(os.path.join(D, "bets_log.csv"), encoding="utf-8")):
    caps[(b["date"].replace("-", ""), b["player"].lower(), b["market"], b["side"])].append(
        (ts(b["captured_utc"]), float(b["line"]), float(b["odds"])))

R = list(csv.DictReader(open(os.path.join(D, "graded_bets.csv"), encoding="utf-8")))
rows = []
for r in R:
    if r["result"] not in ("WIN", "loss"): continue
    p, m, side = r["player"].lower(), r["market"], r["side"]
    gid = pl_game.get((p, r["date"]))
    if not gid: continue
    tip = tipof[gid]; lo = tip - datetime.timedelta(hours=72)
    oline, oodds = float(r["line"]), float(r["odds"])
    ent = None
    for dk in (r["date"], (datetime.datetime.strptime(r["date"], "%Y%m%d") - datetime.timedelta(days=1)).strftime("%Y%m%d")):
        cl = sorted([c for c in caps.get((dk, p, m, side), []) if c[0]], key=lambda x: x[0])
        for c in cl:
            if lo < c[0] < tip:
                ent = c; break
        if ent: break
    if ent is None: continue
    ent_t = ent[0]
    S = [x for x in PS.get((p, m, side, oline), ()) if lo < x[0] < tip]
    if not S: continue
    at_entry = [x for x in S if x[0] <= ent_t + datetime.timedelta(minutes=30)]
    f_ent = at_entry[-1][1] if at_entry else None
    f_cls = S[-1][1]
    L = [x for x in PSL.get((p, m, side), ()) if lo < x[0] < tip]
    pl_ent = [x for x in L if x[0] <= ent_t + datetime.timedelta(minutes=30)]
    rows.append(dict(gid=gid, date=r["date"], player=p, market=m, side=side, src=r["src"],
                     line=oline, odds=oodds, pnl=float(r["pnl"]), result=r["result"],
                     ev_ent=(oodds / f_ent - 1) if f_ent else None, ev_cls=oodds / f_cls - 1,
                     pinn_line_ent=(pl_ent[-1][1] if pl_ent else None), pinn_line_cls=L[-1][1],
                     lag_ent=((ent_t - at_entry[-1][0]).total_seconds() / 3600 if at_entry else None),
                     lag_cls=(tip - S[-1][0]).total_seconds() / 3600))

print("rows with sharp reference: %d  games=%d  markets=%s" % (
    len(rows), len(set(x["gid"] for x in rows)), collections.Counter(x["market"] for x in rows)))
le = [x["lag_ent"] for x in rows if x["lag_ent"] is not None]
print("  entry-time sharp quote staleness median %.2fh (n=%d have one)" % (statistics.median(le), len(le)))
print("  sharp CLOSE quote median %.2fh before tip" % statistics.median([x["lag_cls"] for x in rows]))
with open(os.path.join(D, "outputs", "clv", "sharp_rows.pkl"), "wb") as f: pickle.dump(rows, f)


def bboot(rs, vf, nb=3000):
    bl = collections.defaultdict(list)
    for r in rs:
        v = vf(r)
        if v is not None: bl[r["gid"]].append(v)
    b = list(bl.values())
    if len(b) < 3: return (float("nan"), float("nan"), float("nan"), 0, 0)
    allv = [x for q in b for x in q]; pt = statistics.mean(allv); ms = []
    for _ in range(nb):
        s = [random.choice(b) for _ in range(len(b))]
        fl = [x for q in s for x in q]
        ms.append(sum(fl) / len(fl))
    ms.sort()
    return pt, ms[int(.025 * nb)], ms[int(.975 * nb)], len(allv), len(b)


METRICS = ["ev_ent", "ev_cls"]; POPS = ["ALL", "Over", "Under"]

def cells(rs, metric):
    s = [r for r in rs if r.get(metric) is not None]
    s.sort(key=lambda r: r[metric]); out = []
    k = 5; sz = max(1, len(s) // k)
    for i in range(k): out.append(s[i * sz:(i + 1) * sz if i < k - 1 else len(s)])
    out.append(s[len(s) // 2:]); out.append(s[:len(s) // 2])
    return out

def grid_best(rs, pnlmap):
    best = -9e9; ncells = 0
    for met in METRICS:
        for pop in POPS:
            sub = [r for r in rs if pop == "ALL" or r["side"] == pop]
            for c in cells(sub, met):
                if len(c) < 20: continue
                ncells += 1
                best = max(best, sum(pnlmap[id(r)] for r in c) / len(c))
    return best, ncells

true_pnl = {id(r): r["pnl"] for r in rows}
_, NC = grid_best(rows, true_pnl)
gblocks = collections.defaultdict(list)
for r in rows: gblocks[r["gid"]].append(r)
NB = 1500; nullbest = []
for _ in range(NB):
    keys = list(gblocks.keys()); vals = [[x["pnl"] for x in gblocks[k]] for k in keys]
    random.shuffle(vals)
    pm = {}
    for k, v in zip(keys, vals):
        rs = gblocks[k]
        vv = (v * ((len(rs) // len(v)) + 1))[:len(rs)]
        for r, x in zip(rs, vv): pm[id(r)] = x
    nullbest.append(grid_best(rows, pm)[0])
nullbest.sort()
print("\n### NOISE CEILING (declared grid = %d live cells; game-block permutation of outcomes, %d draws)" % (NC, NB))
print("    best-cell ROI under the null: p50 %+.1f%%   p95 %+.1f%%   p99 %+.1f%%" % (
    nullbest[int(.50 * NB)] * 100, nullbest[int(.95 * NB)] * 100, nullbest[int(.99 * NB)] * 100))
CEIL = nullbest[int(.95 * NB)] * 100

for met, label in (("ev_cls", "EV vs sharp CLOSE (CLV diagnostic, uses future info)"),
                   ("ev_ent", "EV vs sharp AT ENTRY (executable in real time)")):
    print("\n=== %s ===" % label)
    s = [r for r in rows if r.get(met) is not None]
    m = bboot(s, lambda r: r[met])
    print("  mean %s = %+.2f%% [%+.2f,%+.2f]  n=%d games=%d  frac>0 %.1f%%" % (
        met, m[0] * 100, m[1] * 100, m[2] * 100, m[3], m[4], sum(1 for r in s if r[met] > 0) / len(s) * 100))
    print("  %-9s %9s %8s %18s %5s %6s %11s" % ("quintile", "metric%", "ROI%", "CI", "n", "games", "vs ceiling"))
    for i, c in enumerate(cells(s, met)[:5]):
        b = bboot(c, lambda r: r["pnl"])
        flag = "OVER" if b[0] * 100 > CEIL else "under"
        print("  Q%-8d %+9.2f %+8.1f [%+7.1f,%+7.1f] %5d %6d %11s" % (
            i + 1, statistics.mean([r[met] for r in c]) * 100, b[0] * 100, b[1] * 100, b[2] * 100, b[3], b[4], flag))

    def spear(rs, mk):
        xs = sorted(range(len(rs)), key=lambda i: rs[i][mk]); rx = [0] * len(rs)
        for rk, i in enumerate(xs): rx[i] = rk
        ys = sorted(range(len(rs)), key=lambda i: rs[i]["pnl"]); ry = [0] * len(rs)
        for rk, i in enumerate(ys): ry[i] = rk
        mx = statistics.mean(rx); my = statistics.mean(ry)
        num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
        den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
        return num / den if den else 0.0

    obs = spear(s, met)
    gb = collections.defaultdict(list)
    for r in s: gb[r["gid"]].append(r)
    cnt = 0; NP = 2000
    for _ in range(NP):
        keys = list(gb.keys()); vals = [[x["pnl"] for x in gb[k]] for k in keys]; random.shuffle(vals)
        perm = []
        for k, v in zip(keys, vals):
            rs = gb[k]; vv = (v * ((len(rs) // len(v)) + 1))[:len(rs)]
            for r, x in zip(rs, vv): perm.append({met: r[met], "pnl": x})
        if spear(perm, met) >= obs: cnt += 1
    print("  Spearman(metric, pnl) = %+.4f   game-block permutation p = %.4f" % (obs, (cnt + 1) / (NP + 1)))
