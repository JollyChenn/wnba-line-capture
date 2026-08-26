# Q4/Q5 of the WITHIN-GAME TIMING dimension:
#   - TEAM H1/H2 split as a predictor of player overs (GAME/TEAM-block null)
#   - does the book's line implicitly assume a distribution? (line vs median, residual vs timing)
#   - Model S subset behaviour under the timing features
import csv, os, sys, math, random, statistics, datetime, collections, re, json
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])

R = json.load(open(os.path.join(D, "tim_rows.json")))
SCOR = ("pts", "pra", "pr", "pa"); NONS = ("reb", "ast", "ra")

byp = collections.defaultdict(list)
for r in R: byp[r["pl"]].append(r)
for v in byp.values(): v.sort(key=lambda x: x["gt"])
FEAT0 = {p: dict(h1share=v[0]["h1share"], q4share=v[0]["q4share"], qconc=v[0]["qconc"],
                 q4app=v[0]["q4app"], cv=v[0]["cv"]) for p, v in byp.items()}
for r in R: r.update(FEAT0[r["pl"]])

# team_h1 is a TEAM-NIGHT level label (team's season-to-date H1 share, walk-forward)
TN = collections.defaultdict(list)          # (team, gt) -> rows
for r in R: TN[(r["tm"], r["gt"])].append(r)
tn_keys = sorted(TN)
tn_val = {k: TN[k][0]["team_h1"] for k in tn_keys}
print("team-nights %d  rows %d  teams %d" % (len(tn_keys), len(R), len(set(k[0] for k in tn_keys))))
vv = sorted(v for v in tn_val.values() if v is not None)
print("team_h1 p10 %.3f med %.3f p90 %.3f" % (vv[len(vv)//10], vv[len(vv)//2], vv[9*len(vv)//10]))

GRPS = (("ALL", ALL_MK), ("SCOR", SCOR), ("NONS", NONS))
SPLITS = ("HI", "LO", "T3HI", "T3LO")
MINN = 120
CELLS = [(g, gr, s, w) for g, gr in GRPS for s in SPLITS for w in ("over", "under")]
print("TEAM GRID DECLARED: %d cells (1 feature x 3 groups x 4 splits x 2 sides), MINN=%d" % (len(CELLS), MINN))

def team_cells(valmap):
    out = []
    for gname, grp, s_, w in CELLS:
        rows = [r for r in R if r["mk"] in grp and valmap.get((r["tm"], r["gt"])) is not None]
        vals = [valmap[(r["tm"], r["gt"])] for r in rows]
        v = sorted(vals)
        if s_ in ("HI", "LO"):
            c = v[len(v) // 2]
            sel = [r for r, x in zip(rows, vals) if (x >= c if s_ == "HI" else x < c)]
        else:
            lo = v[len(v) // 3]; hi = v[2 * len(v) // 3]
            sel = [r for r, x in zip(rows, vals) if (x >= hi if s_ == "T3HI" else x < lo)]
        if len(sel) < MINN: continue
        if w == "over":
            roi = sum((r["over_od"] - 1) if r["over_won"] else -1.0 for r in sel) / len(sel)
        else:
            roi = sum((r["under_od"] - 1) if not r["over_won"] else -1.0 for r in sel) / len(sel)
        out.append((roi, len(sel), "team_h1 %s [%s] %s" % (s_, w, gname)))
    return out

# NULL: relabel team-nights (the level the label lives at)
NPERM = 1500
best = []
donors = list(tn_keys)
for _ in range(NPERM):
    random.shuffle(donors)
    vm = {k: tn_val[d] for k, d in zip(tn_keys, donors)}
    c = team_cells(vm)
    if c: best.append(max(x[0] for x in c))
best.sort()
CEIL95 = best[int(0.95 * len(best))]
print("TEAM NOISE CEILING (team-night relabel, %d perms): p95 best-cell ROI = %+0.2f%%" % (NPERM, 100 * CEIL95))
real = team_cells(tn_val); real.sort(reverse=True)
for roi, n, lab in real[:6] + real[-4:]:
    pv = (sum(1 for x in best if x >= roi) + 1) / (len(best) + 1)
    print("  %-30s n=%-5d ROI %+6.2f%%  p=%.3f %s" % (lab, n, 100 * roi, pv, "BEATS" if roi > CEIL95 else ""))

# ---------------- Q5: does the LINE implicitly assume a timing distribution? ----------------
print("\n" + "=" * 92)
print("Q5  LINE vs MEDIAN and RESIDUAL, by timing feature")
print("=" * 92)
# rebuild trailing median (team-filtered, >=5 current-team games) for each quote
hist_t = collections.defaultdict(list)
for (pl, tp), row in pgrow.items(): hist_t[pl].append(row)
for v in hist_t.values(): v.sort(key=lambda x: x["tip"])
for r in R:
    gt = datetime.datetime.fromisoformat(r["gt"])
    prior = [x for x in hist_t.get(r["pl"], []) if x["tip"] < gt and x["tm"] == r["tm"]]
    r["medT"] = statistics.median(x[r["mk"]] for x in prior[-10:]) if len(prior) >= 5 else None
    r["linegap"] = (r["line"] - r["medT"]) if r["medT"] is not None else None

def sprho(u, v):
    n = len(u); ru = {}; rv = {}
    for arr, d in ((u, ru), (v, rv)):
        order = sorted(range(n), key=lambda i: arr[i]); i = 0
        while i < n:
            j = i
            while j + 1 < n and arr[order[j + 1]] == arr[order[i]]: j += 1
            rk = (i + j) / 2 + 1
            for k in range(i, j + 1): d[order[k]] = rk
            i = j + 1
    mu = (n + 1) / 2
    su = math.sqrt(sum((ru[i] - mu) ** 2 for i in range(n)))
    sv = math.sqrt(sum((rv[i] - mu) ** 2 for i in range(n)))
    if su == 0 or sv == 0: return 0.0
    return sum((ru[i] - mu) * (rv[i] - mu) for i in range(n)) / (su * sv)

def block_p(rows, key, val, nperm=400):
    obs = sprho([r[key] for r in rows], [r[val] for r in rows])
    pls = sorted(set(r["pl"] for r in rows)); donors = list(pls)
    idx = [r["pl"] for r in rows]; v = [r[val] for r in rows]
    cnt = 0
    for _ in range(nperm):
        random.shuffle(donors)
        mp = dict(zip(pls, donors))
        if abs(sprho([FEAT0[mp[p]][key] for p in idx], v)) >= abs(obs): cnt += 1
    return obs, (cnt + 1) / (nperm + 1)

for grp, name in ((SCOR, "scoring"), (NONS, "non-scor")):
    rows = [r for r in R if r["mk"] in grp and r["linegap"] is not None]
    for k in ("h1share", "q4share", "qconc", "q4app"):
        rho, p = block_p(rows, k, "linegap", 400)
        print("  %-9s linegap(line-median) vs %-8s rho %+0.4f p %.3f n %d" % (name, k, rho, p, len(rows)))

# ---------------- Model S subset ----------------
print("\n" + "=" * 92)
print("MODEL S subset (src in flip/hotover/overshoot, mkt in pra/pr/pts, not-raised) x timing")
print("=" * 92)
srcs = {}
for r in load("bets_log.csv"):
    t = ts(r.get("captured_utc"))
    if not t: continue
    srcs.setdefault(((r.get("player") or "").lower(), r.get("market")), []).append((t, r.get("src")))
ms = [r for r in R if r["mk"] in ("pra", "pr", "pts") and r.get("starred") is True]
print("Model-S-like (not-raised, pra/pr/pts, with timing profile): n=%d" % len(ms))
med = {k: statistics.median(FEAT0[p][k] for p in FEAT0) for k in ("h1share", "q4share", "qconc", "q4app")}
for k in ("h1share", "q4share", "qconc", "q4app"):
    for lab, fn in (("HI", lambda r, k=k: r[k] >= med[k]), ("LO", lambda r, k=k: r[k] < med[k])):
        g = [r for r in ms if fn(r)]
        if len(g) < 60: continue
        roi = sum((r["over_od"] - 1) if r["over_won"] else -1.0 for r in g) / len(g)
        om = statistics.mean(r["over_od"] for r in g)
        se = om / math.sqrt(len(g))
        print("  %-8s %-3s n=%-4d over%% %.1f  ROI %+6.2f%%  CI [%+0.1f, %+0.1f]" % (
            k, lab, len(g), 100 * sum(1 for r in g if r["over_won"]) / len(g), 100 * roi,
            100 * (roi - 1.96 * se), 100 * (roi + 1.96 * se)))
print("\ndone")
