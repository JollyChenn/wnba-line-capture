# TRACK 3 step 8b: corrected noise ceiling for the executable game-market movement grid.
# NULL: the direction the line moved is independent of which side wins -> randomly flip the bet side per game,
# keeping cell membership (|move| threshold) and the real two-sided prices fixed.
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
def mainpick(c): return min(c, key=lambda x: abs(1 / x[3] - 1 / x[4])) if c else None
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

def first(s, f):
    c = [x for x in s if x[f]]; return c[0] if c else None
def last(s, f, tip, before=0.0):
    c = [x for x in s if x[f] and x["t"] < tip - datetime.timedelta(hours=before)]
    return c[-1] if c else None

# build per-game record: (mv, pnl_side1, pnl_side2)
rec = {"sp": [], "to": []}
for g in linked:
    for f in ("sp", "to"):
        a = first(g["snaps"], f); b = last(g["snaps"], f, g["tip"], before=6.0)
        if not (a and b): continue
        mv = b[f][0] - a[f][0]
        ln, o1, o2 = b[f]
        if f == "sp":
            cov = (g["hs"] - g["as_"]) + ln
            if cov == 0: continue
            p1 = (o1 - 1) if cov > 0 else -1.0
            p2 = (o2 - 1) if cov < 0 else -1.0
            s1_is_move = mv < 0          # first team more favoured -> take first team
        else:
            d = (g["hs"] + g["as_"]) - ln
            if d == 0: continue
            p1 = (o1 - 1) if d > 0 else -1.0
            p2 = (o2 - 1) if d < 0 else -1.0
            s1_is_move = mv > 0
        rec[f].append(dict(mid=g["mid"], mv=abs(mv), pfollow=p1 if s1_is_move else p2,
                           pfade=p2 if s1_is_move else p1))
THR = (0.5, 1.0, 1.5); DIRS = ("follow", "fade")
def cellset(f, thr, direction):
    return [(r["pfollow"] if direction == "follow" else r["pfade"]) for r in rec[f] if r["mv"] >= thr]
def cellset_flip(f, thr, direction, flips):
    out = []
    for r in rec[f]:
        if r["mv"] < thr: continue
        d = direction
        if flips[r["mid"]]: d = "fade" if direction == "follow" else "follow"
        out.append(r["pfollow"] if d == "follow" else r["pfade"])
    return out
mids = sorted(set(r["mid"] for f in rec for r in rec[f]))
NB = 4000; nb = []
for _ in range(NB):
    fl = {m: random.random() < .5 for m in mids}
    best = -9e9
    for f in ("sp", "to"):
        for thr in THR:
            for d in DIRS:
                v = cellset_flip(f, thr, d, fl)
                if len(v) >= 20: best = max(best, sum(v) / len(v))
    nb.append(best)
nb.sort()
print("declared grid = 2 markets x 3 thresholds x 2 directions = 12 cells")
print("games: spread n=%d, total n=%d (independent games)" % (len(rec["sp"]), len(rec["to"])))
print("NOISE CEILING (side-flip null, %d draws): best-cell ROI p50 %+.1f%%  p95 %+.1f%%  p99 %+.1f%%" % (
    NB, nb[int(.5 * NB)] * 100, nb[int(.95 * NB)] * 100, nb[int(.99 * NB)] * 100))
CEIL = nb[int(.95 * NB)] * 100
def bboot(v, n=6000):
    ms = [statistics.mean([random.choice(v) for _ in range(len(v))]) for _ in range(n)]
    ms.sort(); return statistics.mean(v), ms[int(.025 * n)], ms[int(.975 * n)]
print("%-8s %-5s %-7s %5s %9s %22s %11s" % ("market", "thr", "dir", "n", "ROI%", "CI", "vs ceiling"))
best_real = -9e9
for f in ("sp", "to"):
    for thr in THR:
        for d in DIRS:
            v = cellset(f, thr, d)
            if len(v) < 20: continue
            m, lo, hi = bboot(v); best_real = max(best_real, m * 100)
            print("%-8s %-5.1f %-7s %5d %+9.1f [%+9.1f,%+9.1f] %11s" % (
                "spread" if f == "sp" else "total", thr, d, len(v), m * 100, lo * 100, hi * 100,
                "OVER" if m * 100 > CEIL else "under"))
print("best real cell %+.1f%% vs p95 ceiling %+.1f%%  ->  %s" % (
    best_real, CEIL, "CLEARS" if best_real > CEIL else "DOES NOT CLEAR"))
