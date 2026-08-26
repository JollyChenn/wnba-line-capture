# TRACK 3 step 8: game-market movement -- proper null, executable momentum, close-vs-open sharpness.
import csv, os, sys, math, statistics, collections, random, datetime
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = r"C:\Users\Axioo\wnba-line-capture"
FULL = {"Atlanta Dream": "ATL", "Chicago Sky": "CHI", "Connecticut Sun": "CON", "Dallas Wings": "DAL",
        "Golden State Valkyries": "GS", "Indiana Fever": "IND", "Los Angeles Sparks": "LA",
        "Las Vegas Aces": "LV", "Minnesota Lynx": "MIN", "New York Liberty": "NY",
        "Phoenix Mercury": "PHX", "Portland Fire": "POR", "Seattle Storm": "SEA",
        "Toronto Tempo": "TOR", "Washington Mystics": "WSH"}
def ts(s):
    s = (s or "").replace("Z", "+00:00")
    try:
        d = datetime.datetime.fromisoformat(s); return d if d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)
    except Exception: return None
def am2dec(a):
    a = float(a); return 1 + (a / 100 if a > 0 else 100 / -a)

GM = list(csv.DictReader(open(os.path.join(D, "data", "games_2026.csv"), encoding="utf-8")))
res = {}
for g in GM:
    try: hs, a = float(g["home_score"]), float(g["away_score"])
    except Exception: continue
    res[(g["home"], g["away"], g["date"])] = (hs, a, ts(g["tip"]))

raw = collections.defaultdict(list); meta = {}
for r in csv.DictReader(open(os.path.join(D, "gamelines.csv"), encoding="utf-8")):
    t = ts(r["captured_utc"])
    if not t: continue
    pr = r["prices"].split(",")
    if len(pr) != 2: continue
    try: d1, d2 = am2dec(pr[0]), am2dec(pr[1])
    except Exception: continue
    raw[r["matchup_id"]].append((t, r["type"], r.get("points", ""), d1, d2))
    meta[r["matchup_id"]] = (r["teams"], ts(r["start"]))

def mainpick(c):
    return min(c, key=lambda x: abs(1 / x[3] - 1 / x[4])) if c else None

linked = []
for mid, rows in raw.items():
    teams, start = meta[mid]
    try: h, a = [FULL[x] for x in teams.split("|")]
    except Exception: continue
    bt = collections.defaultdict(list)
    for x in rows: bt[x[0]].append(x)
    snaps = []
    for t in sorted(bt):
        g = bt[t]
        sp = mainpick([x for x in g if x[1] == "spread" and x[2]])
        to = mainpick([x for x in g if x[1] == "total" and x[2]])
        snaps.append(dict(t=t, sp=(float(sp[2]), sp[3], sp[4]) if sp else None,
                          to=(float(to[2]), to[3], to[4]) if to else None))
    key = None
    for dd in ((start - datetime.timedelta(hours=6)).strftime("%Y%m%d"), start.strftime("%Y%m%d")):
        if (h, a, dd) in res: key = (h, a, dd); break
        if (a, h, dd) in res: key = (a, h, dd); break
    if not key: continue
    hs, aw, tip = res[key]
    if key[0] != h: hs, aw = aw, hs
    linked.append(dict(mid=mid, hs=hs, as_=aw, tip=tip, snaps=snaps))
print("games linked: %d" % len(linked))

def first(s, f):
    c = [x for x in s if x[f]]; return c[0] if c else None
def last(s, f, tip, before=0.0):
    c = [x for x in s if x[f] and x["t"] < tip - datetime.timedelta(hours=before)]
    return c[-1] if c else None
def bboot(v, nb=6000):
    if len(v) < 3: return (float("nan"),) * 3
    ms = [statistics.mean([random.choice(v) for _ in range(len(v))]) for _ in range(nb)]
    ms.sort(); return statistics.mean(v), ms[int(.025 * nb)], ms[int(.975 * nb)]

# ---------------- A) IS THE CLOSE SHARPER THAN THE OPEN?  (validates CLV as a concept in this market)
print("\n=== A) IS THE CLOSING GAME LINE SHARPER THAN THE OPENING LINE? ===")
print("    (diagnostic, NOT a strategy: it uses the close to pick the side and the open line to grade)")
for f, name in (("sp", "spread"), ("to", "total")):
    for thr in (0.25, 1.0):
        w = l = 0
        for g in linked:
            a = first(g["snaps"], f); c = last(g["snaps"], f, g["tip"])
            if not (a and c): continue
            mv = c[f][0] - a[f][0]
            if abs(mv) < thr: continue
            if f == "sp":
                cover = (g["hs"] - g["as_"]) + a["sp"][0]           # first team vs OPENING spread
                if cover == 0: continue
                hit = (cover > 0) == (mv < 0)
            else:
                d = (g["hs"] + g["as_"]) - a["to"][0]
                if d == 0: continue
                hit = (d > 0) == (mv > 0)
            w += hit; l += not hit
        n = w + l
        if n < 15: continue
        p = w / n
        # exact binomial two-sided-ish (one-sided upper tail) under p=0.5, games independent
        pv = sum(math.comb(n, k) for k in range(w, n + 1)) / 2 ** n
        se = math.sqrt(.25 / n)
        print("  %-7s |move|>=%.2f : side the line moved toward beat the OPEN line %d/%d = %.1f%% "
              "[%.1f,%.1f]  binomial p=%.4f" % (name, thr, w, n, p * 100, (p - 1.96 * se) * 100, (p + 1.96 * se) * 100, pv))

# ---------------- B) EXECUTABLE MOMENTUM: decide at T-6h on open->T-6h move, bet at the T-6h price/line
print("\n=== B) EXECUTABLE: observe move open -> T-6h, bet that direction AT T-6h price, grade vs T-6h line ===")
print("    (gate and price at the same instant; no future information)")
GRID = []
for f, name in (("sp", "spread"), ("to", "total")):
    for thr in (0.5, 1.0, 1.5):
        for direction in ("follow", "fade"):
            GRID.append((f, name, thr, direction))
cellrows = {}
for f, name, thr, direction in GRID:
    v = []
    for g in linked:
        a = first(g["snaps"], f); b = last(g["snaps"], f, g["tip"], before=6.0)
        if not (a and b): continue
        mv = b[f][0] - a[f][0]
        if abs(mv) < thr: continue
        sgn = mv if direction == "follow" else -mv
        if f == "sp":
            ln, o1, o2 = b["sp"]; cov = (g["hs"] - g["as_"]) + ln
            if cov == 0: continue
            if sgn < 0: won, price = cov > 0, o1
            else: won, price = cov < 0, o2
        else:
            ln, o1, o2 = b["to"]; d = (g["hs"] + g["as_"]) - ln
            if d == 0: continue
            if sgn > 0: won, price = d > 0, o1
            else: won, price = d < 0, o2
        v.append((won * price - 1, g["mid"]))
    cellrows[(f, thr, direction)] = v
# noise ceiling on this declared grid: permute the per-game outcome sign (games independent)
allmids = sorted(set(g["mid"] for g in linked))
NB = 3000; nb_best = []
pool = {k: v for k, v in cellrows.items() if len(v) >= 20}
for _ in range(NB):
    best = -9e9
    flip = {m: random.random() < .5 for m in allmids}
    for k, v in pool.items():
        # null: outcome of each game independent of the movement label -> resample pnl from the cell's own
        # win/loss set with the cell's base rate implied by prices (breakeven), i.e. shuffle wins across games
        pr = [x[0] for x in v]
        s = [random.choice(pr) if flip[x[1]] else -1.0 for x in v]
        best = max(best, sum(s) / len(s))
    nb_best.append(best)
nb_best.sort()
print("  declared grid = %d cells (2 markets x 3 thresholds x follow/fade); live cells n>=20: %d" % (len(GRID), len(pool)))
print("  NOISE CEILING best-cell ROI under game-level null: p50 %+.1f%%  p95 %+.1f%%  p99 %+.1f%%" % (
    nb_best[int(.5 * NB)] * 100, nb_best[int(.95 * NB)] * 100, nb_best[int(.99 * NB)] * 100))
CEIL = nb_best[int(.95 * NB)] * 100
print("  %-8s %-6s %-7s %5s %9s %20s %10s" % ("market", "thr", "dir", "n", "ROI%", "CI", "vs ceiling"))
for (f, thr, direction), v in sorted(cellrows.items()):
    if len(v) < 15: continue
    m, lo, hi = bboot([x[0] for x in v])
    print("  %-8s %-6.1f %-7s %5d %+9.1f [%+8.1f,%+8.1f] %10s" % (
        "spread" if f == "sp" else "total", thr, direction, len(v), m * 100, lo * 100, hi * 100,
        "OVER" if m * 100 > CEIL else "under"))

# ---------------- C) closing-price CLV of the game markets themselves
print("\n=== C) HOW BIG IS GAME-MARKET CLV AT ALL? (open price vs close price, main lines) ===")
for f, name in (("sp", "spread"), ("to", "total")):
    dl = []; dp = []
    for g in linked:
        a = first(g["snaps"], f); c = last(g["snaps"], f, g["tip"])
        if not (a and c): continue
        dl.append(abs(c[f][0] - a[f][0]))
        dp.append(abs(c[f][1] / a[f][1] - 1))
    print("  %-7s mean |line move| %.2f pts (unchanged %.0f%%), mean |price move| %.2f%%  n=%d games" % (
        name, statistics.mean(dl), sum(1 for x in dl if x < 1e-6) / len(dl) * 100, statistics.mean(dp) * 100, len(dl)))
